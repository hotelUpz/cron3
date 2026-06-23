# ==============================================================================
# Path: CORE/analytics.py
# Role: Домен аналитики и ведения журнала сделок
# ==============================================================================

import asyncio
import json
import logging
import csv
from datetime import datetime, timezone
from pathlib import Path
from consts import DATA_DIR, ANALYTICS_CSV_MAX_ROWS

logger = logging.getLogger("Analytics")

class AnalyticsManager:
    """
    Ведет журнал сделок и статистику закрытых позиций.
    """
    def __init__(self):
        self.log_file = DATA_DIR / "analytics.json"
        self.csv_file = DATA_DIR / "trades_ledger.csv"
        self._lock = asyncio.Lock()
        self._csv_lock = asyncio.Lock()
        self._background_tasks = set()
        self._ensure_files()

    def _ensure_files(self):
        if not self.log_file.exists():
            default_data = {
                "initial_balance_usdt": 82.0,
                "current_balance_usdt": 82.0,
                "total_trades": 0,
                "winning_trades": 0,
                "winrate_pct": 0.0,
                "total_trading_pnl_usdt": 0.0,
                "total_pnl_usdt": 0.0,
                "total_drawdown_usdt": 0.0,
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

    async def _append_to_csv(self, symbol: str, side: str, open_time: int, close_time: int, pnl: float):
        async with self._csv_lock:
            try:
                def ts_to_str(ts_ms):
                    if not ts_ms:
                        return "Unknown"
                    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                open_str = ts_to_str(open_time)
                close_str = ts_to_str(close_time)

                # Append the new row
                with open(self.csv_file, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([symbol, side, open_str, close_str, pnl])
                
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
            total_unrealized = float(acc_data.get("totalUnrealizedProfit", 0.0))
            margin_balance = float(acc_data.get("totalMarginBalance", 0.0))
            
            data["total_drawdown_usdt"] = round(total_unrealized, 4)
            data["current_balance_usdt"] = round(margin_balance, 4)
            
            initial_bal = float(data.get("initial_balance_usdt", 0.0))
            if initial_bal > 0:
                data["total_pnl_usdt"] = round(margin_balance - initial_bal, 4)
            
            positions = acc_data.get("positions", [])
            for p in positions:
                sym = p.get("symbol", "")
                if sym in data["per_coin"]:
                    unrealized = float(p.get("unRealizedProfit", 0.0))
                    # Binance returns separate long/short positions for Hedge mode, we need to sum them
                    side_key = p.get("positionSide")
                    
                    if "current_drawdown" not in data["per_coin"][sym]:
                        data["per_coin"][sym]["current_drawdown"] = 0.0
                    
                    # Since we reset below, we just sum up the active ones.
                    # Wait, we need to iterate positions and sum them.
                    pass
            
            # Recalculate correctly
            coin_drawdowns = {}
            for p in positions:
                sym = p.get("symbol", "")
                unrealized = float(p.get("unrealizedProfit", 0.0))
                coin_drawdowns[sym] = coin_drawdowns.get(sym, 0.0) + unrealized
                
            for sym, drawdown in coin_drawdowns.items():
                if sym in data["per_coin"]:
                    data["per_coin"][sym]["current_drawdown"] = round(drawdown, 4)
                    
        except Exception as e:
            logger.error(f"Error updating drawdowns: {e}")

    async def _fetch_and_record(self, client, symbol: str, side: str, open_time: int, close_time: int):
        # Если open_time нет (например, бот запущен с уже открытой позицией)
        if open_time == 0:
            logger.warning(f"[{symbol}] {side} closed, but open_time is 0. Using last 5 minutes for PnL to avoid pulling entire history.")
            start_time_param = close_time - (5 * 60 * 1000)
        else:
            start_time_param = open_time

        # Ждем немного, чтобы биржа успела рассчитать PnL (иногда есть задержка)
        await asyncio.sleep(2.0)
        
        pnl = 0.0
        try:
            fetched_pnl = await client.get_realized_pnl(symbol, start_time_param, close_time)
            if fetched_pnl is not None:
                pnl = fetched_pnl
        except Exception as e:
            logger.error(f"[{symbol}] Error fetching realized PnL: {e}")

        # Update CSV
        await self._append_to_csv(symbol, side, open_time, close_time, pnl)

        async with self._lock:
            data = self._read_data()
            if not data:
                return
            
            # Remove legacy trades_ledger if present to keep JSON clean
            if "trades_ledger" in data:
                del data["trades_ledger"]
            
            is_win = 1 if pnl > 0 else 0
            
            # Global Stats
            data["total_trades"] = data.get("total_trades", 0) + 1
            data["winning_trades"] = data.get("winning_trades", 0) + is_win
            data["total_trading_pnl_usdt"] = round(data.get("total_trading_pnl_usdt", 0.0) + pnl, 4)
            data["winrate_pct"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
            
            # Per-Coin Stats
            if "per_coin" not in data:
                data["per_coin"] = {}
            if symbol not in data["per_coin"]:
                data["per_coin"][symbol] = {"total_trades": 0, "winning_trades": 0, "winrate_pct": 0.0, "total_pnl_usdt": 0.0, "current_drawdown": 0.0}
            
            coin_stat = data["per_coin"][symbol]
            coin_stat["total_trades"] += 1
            coin_stat["winning_trades"] += is_win
            coin_stat["total_pnl_usdt"] = round(coin_stat["total_pnl_usdt"] + pnl, 4)
            coin_stat["winrate_pct"] = round((coin_stat["winning_trades"] / coin_stat["total_trades"]) * 100, 2)
            
            # Update Drawdowns
            await self._update_drawdowns(client, data)
            
            self._write_data(data)
            
        logger.info(f"[ANALYTICS] Position finished: {symbol} {side} PnL={pnl}")
