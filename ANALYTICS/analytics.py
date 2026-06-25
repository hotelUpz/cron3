# ==============================================================================
# Path: ANALYTICS/analytics.py
# Role: Домен аналитики и ведения журнала сделок
# ==============================================================================

import asyncio
import json
import logging
import csv
from datetime import datetime, timezone
from pathlib import Path
from consts import ANALYTICS_DIR, ANALYTICS_CSV_MAX_ROWS

logger = logging.getLogger("Analytics")

class AnalyticsManager:
    """
    Ведет журнал сделок и статистику закрытых позиций.
    """
    def __init__(self):
        self.log_file = ANALYTICS_DIR / "analytics.json"
        self.csv_file = ANALYTICS_DIR / "trades_ledger.csv"
        self._lock = asyncio.Lock()
        self._csv_lock = asyncio.Lock()
        self._background_tasks = set()
        self._ensure_files()

    def _ensure_files(self):
        if not self.log_file.exists():
            default_data = {
                "start_balance_usdt": 82.0,
                "cur_balance_usdt": 82.0,
                "total_trades": 0,
                "winning_trades": 0,
                "winrate_pct": 0.0,
                "gross_profit_usdt": 0.0,
                "net_profit_usdt": 0.0,
                "unrealized_pnl_usdt": 0.0,
                "per_coin": {}
            }
            self.log_file.write_text(json.dumps(default_data, indent=4), encoding="utf-8")
        
        if not self.csv_file.exists():
            with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Symbol", "Side", "Open Time", "Close Time", "PnL (USDT)"])

    def _read_data(self) -> dict:
        try:
            return json.loads(self.log_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading analytics file: {e}")
            return {}

    def _write_data(self, data: dict):
        try:
            self.log_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error writing analytics file: {e}")

    async def _append_to_csv(self, symbol: str, side: str, open_time: int, close_time: int, pnl: float, balance: float):
        async with self._csv_lock:
            try:
                def ts_to_str(ts_ms):
                    if not ts_ms:
                        return "Unknown"
                    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                open_str = ts_to_str(open_time)
                close_str = ts_to_str(close_time)

                # Check if we need to write header
                file_exists = self.csv_file.exists()
                if not file_exists:
                    with open(self.csv_file, mode="w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["Symbol", "Side", "Open Time", "Close Time", "PnL", "Balance"])

                # Append the new row
                with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([symbol, side, open_str, close_str, pnl, balance])
                
                # Truncate if necessary
                with open(self.csv_file, mode="r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                if len(lines) > ANALYTICS_CSV_MAX_ROWS + 1: # +1 for header
                    lines = [lines[0]] + lines[-(ANALYTICS_CSV_MAX_ROWS):]
                    with open(self.csv_file, mode="w", encoding="utf-8", newline="") as f:
                        f.writelines(lines)
            except Exception as e:
                logger.error(f"Error appending to CSV: {e}")



    def record_finished_position(self, client, symbol: str, side: str, open_time: int, close_time: int):
        """Запускает фоновую задачу для подтягивания PnL и записи в лог."""
        task = asyncio.create_task(self._fetch_and_record(client, symbol, side, open_time, close_time))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _update_drawdowns(self, client, data: dict):
        """Fetches account info to update current unrealized drawdowns globally and per-coin."""
        try:
            res = await client.fetch_account_info()
            if not res.success or not isinstance(res.data, dict):
                return
            
            acc_data = res.data
            
            positions = acc_data.get("positions", [])
            coin_drawdowns = {}
            for p in positions:
                sym = p.get("symbol", "")
                unrealized = float(p.get("unrealizedProfit", 0.0))
                coin_drawdowns[sym] = coin_drawdowns.get(sym, 0.0) + unrealized
                
            bot_unrealized = 0.0
            for sym, drawdown in coin_drawdowns.items():
                if sym in data.get("per_coin", {}):
                    data["per_coin"][sym]["current_drawdown"] = round(drawdown, 4)
                    bot_unrealized += drawdown
                    
            # unrealized_pnl_usdt = Сум по current_drawdown
            data["unrealized_pnl_usdt"] = round(bot_unrealized, 4)
            
            # gross_profit_usdt = Сум по net_profit_usdt пер символ
            bot_gross_profit = 0.0
            if "per_coin" in data:
                bot_gross_profit = sum(c.get("net_profit_usdt", 0.0) for c in data["per_coin"].values())
            data["gross_profit_usdt"] = round(bot_gross_profit, 4)
            
            # net_profit_usdt = gross_profit_usdt + unrealized_pnl_usdt (так как unrealized отрицательный, мы прибавляем его, чтобы вычесть просадку из профита)
            data["net_profit_usdt"] = round(bot_gross_profit + bot_unrealized, 4)
            
            initial = float(data.get("start_balance_usdt", 0.0))
            bot_cur_balance = round(initial + data["net_profit_usdt"], 4)
            data["cur_balance_usdt"] = bot_cur_balance
            
            if initial > 0:
                data["roi_pct"] = round(((bot_cur_balance - initial) / initial) * 100, 2)
            else:
                data["roi_pct"] = 0.0
                
            if bot_gross_profit > 0:
                data["load_ratio"] = round(abs(bot_unrealized) / bot_gross_profit, 2)
            else:
                data["load_ratio"] = 0.0
                    
            # Isolate unrealized PnL to ONLY the coins this bot tracks in analytics
            data["unrealized_pnl_usdt"] = round(bot_unrealized, 4)
                    
        except Exception as e:
            logger.error(f"Error updating drawdowns: {e}")

    def start_realtime_tracker(self, client):
        if hasattr(self, "_tracker_task") and self._tracker_task:
            return
        self._tracker_task = asyncio.create_task(self._realtime_tracker_loop(client))
        self._background_tasks.add(self._tracker_task)
        self._tracker_task.add_done_callback(self._background_tasks.discard)
        
    async def _realtime_tracker_loop(self, client):
        logger.info("[ANALYTICS] Started real-time absolute drawdown tracker (polls every 15s)")
        while True:
            await asyncio.sleep(15.0)
            try:
                async with self._lock:
                    data = self._read_data()
                    if not data:
                        continue
                        
                    res = await client.fetch_account_info()
                    if not res.success or not isinstance(res.data, dict):
                        continue
                        
                    margin_balance = float(res.data.get("totalMarginBalance", 0.0))
                    
                    # Update global unrealized pnl as well
                    positions = res.data.get("positions", [])
                    coin_drawdowns = {}
                    for p in positions:
                        sym = p.get("symbol", "")
                        unrealized = float(p.get("unrealizedProfit", 0.0))
                        coin_drawdowns[sym] = coin_drawdowns.get(sym, 0.0) + unrealized
                    bot_unrealized = 0.0
                    for sym, drawdown in coin_drawdowns.items():
                        if sym in data.get("per_coin", {}):
                            data["per_coin"][sym]["current_drawdown"] = round(drawdown, 4)
                            bot_unrealized += drawdown
                    data["unrealized_pnl_usdt"] = round(bot_unrealized, 4)
                    
                    bot_gross_profit = 0.0
                    if "per_coin" in data:
                        bot_gross_profit = sum(c.get("net_profit_usdt", 0.0) for c in data["per_coin"].values())
                    data["gross_profit_usdt"] = round(bot_gross_profit, 4)
                    data["net_profit_usdt"] = round(bot_gross_profit + bot_unrealized, 4)
                    
                    initial = data.get("start_balance_usdt", 0.0)
                    bot_cur_balance = round(initial + data["net_profit_usdt"], 4)
                    data["cur_balance_usdt"] = bot_cur_balance
                    
                    if initial > 0:
                        data["roi_pct"] = round(((bot_cur_balance - initial) / initial) * 100, 2)
                    else:
                        data["roi_pct"] = 0.0
                        
                    if bot_gross_profit > 0:
                        data["load_ratio"] = round(abs(bot_unrealized) / bot_gross_profit, 2)
                    else:
                        data["load_ratio"] = 0.0
                    
                    peak = data.get("peak_balance_usdt", initial)
                    trough = data.get("min_balance_usdt", peak)
                    
                    changed = False
                    if bot_cur_balance > peak:
                        peak = bot_cur_balance
                        trough = bot_cur_balance
                        data["peak_balance_usdt"] = peak
                        data["min_balance_usdt"] = trough
                        changed = True
                        
                    if bot_cur_balance < trough:
                        trough = bot_cur_balance
                        data["min_balance_usdt"] = trough
                        changed = True
                        
                    # Always write data to update unrealized PnL, not just on peak/trough change
                    max_drawdown = trough - peak
                    data["max_drawdown_usdt"] = round(min(data.get("max_drawdown_usdt", 0.0), max_drawdown), 4)
                    
                    max_perf = peak - initial
                    data["performance_usdt"] = round(max(data.get("performance_usdt", 0.0), max_perf), 4)
                    
                    if data["max_drawdown_usdt"] < 0:
                        data["recovery_factor"] = round(bot_gross_profit / abs(data["max_drawdown_usdt"]), 2)
                    else:
                        data["recovery_factor"] = 0.0
                    
                    import time
                    data["last_updated_ts"] = int(time.time() * 1000)
                    
                    self._write_data(data)
            except Exception as e:
                logger.error(f"Realtime tracker error: {e}")

    async def _fetch_and_record(self, client, symbol: str, side: str, open_time: int, close_time: int):
        # Если open_time нет (например, бот запущен с уже открытой позицией)
        if open_time == 0:
            logger.warning(f"[{symbol}] {side} closed, but open_time is 0. Using last 5 minutes for PnL to avoid pulling entire history.")
            start_time_param = close_time - (5 * 60 * 1000)
        else:
            start_time_param = open_time

        # Ждем немного, чтобы биржа успела рассчитать PnL (иногда есть задержка)
        await asyncio.sleep(2.0)
        
        gross_pnl = 0.0
        commission = 0.0
        funding_fee = 0.0
        net_pnl = 0.0
        try:
            fetched_data = await client.get_income_pnl(symbol, start_time_param, close_time)
            if fetched_data is not None:
                gross_pnl = fetched_data.get("gross_pnl", 0.0)
                commission = fetched_data.get("commission", 0.0)
                funding_fee = fetched_data.get("funding_fee", 0.0)
                net_pnl = fetched_data.get("net_pnl", 0.0)
        except Exception as e:
            logger.error(f"[{symbol}] Error fetching income PnL: {e}")

        async with self._lock:
            data = self._read_data()
            if not data:
                return
            
            # Remove legacy trades_ledger if present to keep JSON clean
            if "trades_ledger" in data:
                del data["trades_ledger"]
            
            is_win = 1 if net_pnl > 0 else 0
            
            # Global Stats
            data["total_trades"] = data.get("total_trades", 0) + 1
            data["winning_trades"] = data.get("winning_trades", 0) + is_win
            data["total_commission_usdt"] = round(data.get("total_commission_usdt", 0.0) + commission, 4)
            data["total_funding_usdt"] = round(data.get("total_funding_usdt", 0.0) + funding_fee, 4)
            data["winrate_pct"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
            
            # Per-Coin Stats
            if "per_coin" not in data:
                data["per_coin"] = {}
            if symbol not in data["per_coin"]:
                data["per_coin"][symbol] = {
                    "total_trades": 0, 
                    "winning_trades": 0, 
                    "winrate_pct": 0.0, 
                    "net_profit_usdt": 0.0,
                    "commission_usdt": 0.0,
                    "funding_usdt": 0.0,
                    "current_drawdown": 0.0
                }
            
            coin_stat = data["per_coin"][symbol]
            coin_stat["total_trades"] += 1
            coin_stat["winning_trades"] += is_win
            coin_stat["commission_usdt"] = round(coin_stat.get("commission_usdt", 0.0) + commission, 4)
            coin_stat["funding_usdt"] = round(coin_stat.get("funding_usdt", 0.0) + funding_fee, 4)
            coin_stat["net_profit_usdt"] = round(coin_stat.get("net_profit_usdt", 0.0) + net_pnl, 4)
            coin_stat["winrate_pct"] = round((coin_stat["winning_trades"] / coin_stat["total_trades"]) * 100, 2)
            
            # Update Drawdowns (will also calculate global net_profit_usdt based on margin balance)
            await self._update_drawdowns(client, data)
            current_balance = data.get("cur_balance_usdt", 0.0)
            
            # Update CSV with new balance
            await self._append_to_csv(symbol, side, open_time, close_time, net_pnl, current_balance)
            
            # Cashflow tracking is now merged into trades_ledger via _append_to_csv
            # Max Performance & Drawdown
            initial = data.get("start_balance_usdt", 0.0)
            peak = data.get("peak_balance_usdt", initial)
            trough = data.get("min_balance_usdt", peak)
            
            if current_balance > peak:
                peak = current_balance
                trough = current_balance # Reset trough when new peak is hit
                
            if current_balance < trough:
                trough = current_balance
                
            data["peak_balance_usdt"] = peak
            data["min_balance_usdt"] = trough
            
            max_drawdown = trough - peak
            data["max_drawdown_usdt"] = round(min(data.get("max_drawdown_usdt", 0.0), max_drawdown), 4)
            
            max_perf = peak - initial
            data["performance_usdt"] = round(max(data.get("performance_usdt", 0.0), max_perf), 4)
            
            gross_pnl = data.get("gross_profit_usdt", 0.0)
            if data["max_drawdown_usdt"] < 0:
                data["recovery_factor"] = round(gross_pnl / abs(data["max_drawdown_usdt"]), 2)
            else:
                data["recovery_factor"] = 0.0
            
            import time
            data["last_updated_ts"] = int(time.time() * 1000)
            
            self._write_data(data)
            
        logger.info(f"[ANALYTICS] Position finished: {symbol} {side} NetPnL={net_pnl}")
