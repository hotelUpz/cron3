# ==============================================================================
# Path: CORE/analytics.py
# Role: Домен аналитики и ведения журнала сделок
# ==============================================================================

import asyncio
import json
import logging
from pathlib import Path
from consts import DATA_DIR

logger = logging.getLogger("Analytics")

class AnalyticsManager:
    """
    Ведет журнал сделок и статистику закрытых позиций.
    """
    def __init__(self):
        self.log_file = DATA_DIR / "runtime_analytics.json"
        self._lock = asyncio.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not self.log_file.exists():
            default_data = {
                "total_positions_LONG": 0,
                "total_positions_SHORT": 0,
                "total_pnl_usdt": 0.0,
                "trades_ledger": []
            }
            self.log_file.write_text(json.dumps(default_data, indent=4), encoding="utf-8")

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

    def record_finished_position(self, client, symbol: str, side: str, open_time: int, close_time: int):
        """Запускает фоновую задачу для подтягивания PnL и записи в лог."""
        asyncio.create_task(self._fetch_and_record(client, symbol, side, open_time, close_time))

    async def _fetch_and_record(self, client, symbol: str, side: str, open_time: int, close_time: int):
        # Если open_time нет (например, бот запущен с уже открытой позицией)
        if open_time == 0:
            logger.warning(f"[{symbol}] {side} closed, but open_time is 0. PnL calculation may be inaccurate.")
            start_time_param = None
        else:
            start_time_param = open_time

        # Ждем немного, чтобы биржа успела рассчитать PnL (иногда есть задержка)
        await asyncio.sleep(2.0)
        
        # client.get_realized_pnl returns float
        pnl = await client.get_realized_pnl(symbol, start_time_param, close_time)
        if pnl is None:
            pnl = 0.0

        async with self._lock:
            data = self._read_data()
            if not data:
                return
            
            # Обновляем счетчики
            if side == "LONG":
                data["total_positions_LONG"] = data.get("total_positions_LONG", 0) + 1
            else:
                data["total_positions_SHORT"] = data.get("total_positions_SHORT", 0) + 1
                
            data["total_pnl_usdt"] = data.get("total_pnl_usdt", 0.0) + pnl
            
            # Запись в ledger
            trade_entry = {
                "symbol": symbol,
                "side": side,
                "open_time": open_time,
                "close_time": close_time,
                "pnl_usdt": pnl
            }
            if "trades_ledger" not in data:
                data["trades_ledger"] = []
            data["trades_ledger"].append(trade_entry)
            
            self._write_data(data)
            
        logger.info(f"[ANALYTICS] Position finished: {symbol} {side} PnL={pnl}")
