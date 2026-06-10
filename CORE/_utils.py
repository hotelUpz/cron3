# ==============================================================================
# Path: CORE/trade_math.py
# Role: Математика для трейдинга (расчет объема, тейк-профитов и прочего)
# ==============================================================================

from typing import Dict, Any
from c_utils import Utils

class TradeMath:
    @staticmethod
    def calculate_order_volume(
        invest_size: float, 
        volume_percent: float, 
        price: float, 
        symbol_info: Dict[str, Any], 
        symbol: str
    ) -> float:
        """
        Рассчитывает количество контрактов (volume) для постановки ордера.
        volume_percent - доля в процентах от invest_size (например, 20 означает 20%).
        """
        precisions = Utils.get_spec_precisions(symbol_info, symbol)
        qty_precision = precisions[0] if precisions else 3
        
        # invest_size (например, 100 USDT). Доля в USDT:
        usdt_volume = invest_size * (volume_percent / 100.0)
        
        # Количество монет:
        coin_qty = usdt_volume / price
        
        # Округляем до нужного количества знаков после запятой (шаг лота)
        return round(coin_qty, qty_precision)

    @staticmethod
    def calculate_take_profit_price(
        avg_entry_price: float, 
        tp_percent_indent: float, 
        side: str, 
        symbol_info: Dict[str, Any], 
        symbol: str
    ) -> float:
        """
        Рассчитывает цену лимитного Take-Profit.
        tp_percent_indent - процент отступа (берем по модулю, т.к. направление определяется логикой).
        Для LONG: TP выше средней цены входа.
        Для SHORT: TP ниже средней цены входа.
        """
        precisions = Utils.get_spec_precisions(symbol_info, symbol)
        price_precision = precisions[1] if precisions else 2
        
        indent_abs = abs(tp_percent_indent)
        
        if side.upper() == "LONG":
            tp_price = avg_entry_price * (1 + indent_abs / 100.0)
        elif side.upper() == "SHORT":
            tp_price = avg_entry_price * (1 - indent_abs / 100.0)
        else:
            tp_price = avg_entry_price
            
        return round(tp_price, price_precision)

    @staticmethod
    def calculate_grid_price(
        initial_price: float,
        indent_pct: float,
        side: str,
        symbol_info: Dict[str, Any],
        symbol: str
    ) -> float:
        """
        Рассчитывает цену следующего уровня сетки на основе отступа.
        Знак indent_pct игнорируется (берется по модулю).
        Для LONG цена усреднения ниже входа: initial_price * (1 - indent_abs / 100.0)
        Для SHORT цена усреднения выше входа: initial_price * (1 + indent_abs / 100.0)
        """
        precisions = Utils.get_spec_precisions(symbol_info, symbol)
        price_precision = precisions[1] if precisions else 2
        
        indent_abs = abs(indent_pct)
        
        if side.upper() == "LONG":
            price = initial_price * (1 - indent_abs / 100.0)
        elif side.upper() == "SHORT":
            price = initial_price * (1 + indent_abs / 100.0)
        else:
            price = initial_price
            
        return round(price, price_precision)

    @staticmethod
    def round_qty(
        qty: float,
        symbol_info: Dict[str, Any],
        symbol: str
    ) -> float:
        """
        Округляет объем до требуемой спецификацией точности.
        """
        precisions = Utils.get_spec_precisions(symbol_info, symbol)
        qty_precision = precisions[0] if precisions else 3
        return round(qty, qty_precision)
# ==============================================================================
# Path: CORE/risk_utils.py
# Role: Общие утилиты для расчетов рисков и детерминации уровней
# ==============================================================================

from typing import Dict, Any

class RiskCalculatingUtils:
    @staticmethod
    def get_current_grid_level(grid: dict) -> str:
        """
        Определяет текущий активный уровень сетки на основе флагов is_active.
        Возвращает строковый ключ уровня (например, "0", "1", "2").
        """
        active_levels = [int(k) for k, v in grid.items() if v.get("is_active")]
        return str(max(active_levels)) if active_levels else "0"
# ==============================================================================
# Path: CORE/spec_manager.py
# Role: Периодическое обновление спецификаций рынка
# ==============================================================================

import asyncio
from typing import Optional, Callable, Dict, Any
from consts import SPEC_TTL_SEC
from API.BINANCE.public import BinancePublic
from c_log import UnifiedLogger

class SpecManager:
    """
    Периодически опрашивает /fapi/v1/exchangeInfo и хранит спецификации символов
    в атрибуте exchange_info.
    """
    def __init__(self, logger: UnifiedLogger, stop_flag: Callable[[], bool]):
        self.logger = logger
        self.stop_flag = stop_flag
        
        self.exchange_info: Optional[Dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запускает фоновый опрос спецификаций"""
        self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        while not self.stop_flag():
            try:
                data = await BinancePublic._get("/fapi/v1/exchangeInfo")
                if isinstance(data, dict) and "symbols" in data:
                    self.exchange_info = data
                else:
                    self.logger.warning("Не удалось получить корректный exchangeInfo")
            except Exception as e:
                self.logger.error(f"Ошибка получения спецификаций: {e}")

            # Ждём SPEC_TTL_SEC секунд (SPEC_TTL_SEC задан в секундах)
            sleep_sec = SPEC_TTL_SEC
            for _ in range(sleep_sec):
                if self.stop_flag():
                    break
                await asyncio.sleep(1)

    async def wait_for_instruments(self, timeout: float = 15.0) -> bool:
        """Ждёт, пока спецификации не загрузятся первый раз."""
        step = 0.1
        elapsed = 0.0
        while elapsed < timeout:
            if self.stop_flag():
                return False
            if self.exchange_info is not None:
                return True
            await asyncio.sleep(step)
            elapsed += step
        
        self.logger.error("Таймаут ожидания exchangeInfo")
        return False

    async def shutdown(self):
        """Останавливает фоновый опрос."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
