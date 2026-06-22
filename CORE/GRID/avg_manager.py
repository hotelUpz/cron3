# ==============================================================================
# Path: CORE/avg_manager.py
# Role: Менеджер усреднений (Grid Manager)
# ==============================================================================

import asyncio
from c_log import UnifiedLogger
from CORE._utils import TradeMath
from c_utils import Utils

logger = UnifiedLogger("AvgManager")

class AverageManager:
    def __init__(self):
        # Флаг для отслеживания того, что расчет сетки для (symbol, side) уже проведен
        self._grid_calculated = set()

    def reset(self, symbol: str, side: str):
        """Сбрасывает флаг расчета сетки (вызывается при закрытии позиции)."""
        key = f"{symbol}_{side}"
        if key in self._grid_calculated:
            self._grid_calculated.remove(key)

    async def _init_grid_prices(self, runtime_manager, symbol: str, side: str, state, spec_data: dict) -> bool:
        """Единожды рассчитывает цены для всей сетки на основе initial_entry_price."""
        grid = state.grid
        initial_price = state.initial_entry_price
        
        # Защита: если WS еще не подтянул initial_price, но есть avg_entry_price
        if initial_price == 0.0 and state.avg_entry_price > 0:
            initial_price = state.avg_entry_price
            state.initial_entry_price = initial_price

        if initial_price <= 0:
            return False # Еще нет цены для расчета
            
        needs_save = False
        for level_str, level_data in grid.items():
            if level_str == "0":
                if not level_data.get("is_active"):
                    level_data["is_active"] = True
                    level_data["price"] = initial_price
                    needs_save = True
            elif level_data.get("price") is None:
                indent_pct = level_data["indent"]
                price = TradeMath.calculate_grid_price(initial_price, indent_pct, side, spec_data, symbol)
                level_data["price"] = price
                needs_save = True
                
        # Предрасчет цен для фолбеков (экономия ресурсов)
        for level_str, tp_data in state.tp_map.items():
            base_price = grid[level_str].get("price")
            if base_price:
                if tp_data.get("fallback_price") is None:
                    fb_indent = tp_data.get("fallback_indent", tp_data["indent"] * 1.5)
                    fb_price = TradeMath.calculate_take_profit_price(base_price, fb_indent, side, spec_data, symbol)
                    tp_data["fallback_price"] = fb_price
                    needs_save = True

        if needs_save:
            # Не вызываем save_cache здесь, это будет сделано в sync_with_fsm
            pass
            
        return True # Расчет проведен

    async def process(self, client, runtime_manager, symbol: str, side: str, state, current_price: float, spec_data: dict, tp_manager):
        """Проверяет и выполняет логику усреднения для позиции."""
        if not state.in_position or state.pending_avg:
            return

        grid = state.grid

        # 1. Единоразовый расчет сетки цен
        key = f"{symbol}_{side}"
        if key not in self._grid_calculated:
            success = await self._init_grid_prices(runtime_manager, symbol, side, state, spec_data)
            if success:
                self._grid_calculated.add(key)
                grid = state.grid
            else:
                return

        # 2. Детерминация цены (кешируем только прайс для горячего пути)
        if state.next_avg_price is None:
            # Сортируем ключи как числа, чтобы идти по порядку уровней
            for level_str in sorted(grid.keys(), key=lambda x: int(x)):
                if level_str == "0":
                    continue
                data = grid[level_str]
                if not data.get("is_active") and data.get("price") is not None:
                    state.next_avg_price = data["price"]
                    break

        if state.next_avg_price is None:
            return

        target_price = state.next_avg_price
        
        # 3. Проверяем условие триггера
        triggered = False
        if side == "LONG" and current_price <= target_price:
            triggered = True
        elif side == "SHORT" and current_price >= target_price:
            triggered = True

        # 4. Выполняем усреднение
        if triggered:
            # Ищем какой именно уровень был триггернут
            next_level = None
            for level_str, data in grid.items():
                if data.get("price") == target_price and not data.get("is_active"):
                    next_level = level_str
                    break
                    
            if not next_level:
                state.next_avg_price = None
                return
                
            logger.info(f"[{symbol}] {side} Averaging triggered for level {next_level} at price {target_price} (current: {current_price})")
            
            # Ставим флаг идемпотентности, запоминаем текущую среднюю
            state.pending_avg = True
            state.pre_avg_price = state.avg_entry_price
            grid[next_level]["is_active"] = True
            
            # Асинхронно ставим ордер и ждем завершения полного пайплайна
            await self._execute_averaging_order(
                client, runtime_manager, symbol, side, next_level, grid[next_level], current_price, spec_data, state, tp_manager
            )

    async def _execute_averaging_order(self, client, runtime_manager, symbol, side, level_str, level_data, current_price, spec_data, state, tp_manager):
        invest_size = runtime_manager.caches[symbol][side].get("invest_size", 100) # берем из статического кэша
        volume_pct = level_data["volume"]
        
        # 1. ОТМЕНА СТАРЫХ ЛИМИТНЫХ ОРДЕРОВ (ВКЛЮЧАЯ ТЕЙК ПРОФИТ) ДО УСРЕДНЕНИЯ
        logger.info(f"[{symbol}] {side} Canceling all limit orders before averaging...")
        await client.cancel_orders_for_side(symbol, side)

        volume = TradeMath.calculate_order_volume(invest_size, volume_pct, current_price, spec_data, symbol)
        order_side = "BUY" if side == "LONG" else "SELL"
        
        # 2. ПОКУПКА ПО РЫНКУ
        logger.info(f"[{symbol}] Opening {side} averaging market order. Level: {level_str}, Volume: {volume}")
        res = await client.make_order(
            symbol=symbol,
            qty=volume,
            side=order_side,
            position_side=side,
            market_type="MARKET"
        )
        
        if not res.success:
            logger.error(f"[{symbol}] Failed to open {side} averaging position: {res.error_msg}")
            # Rollback in case of failure
            level_data["is_active"] = False
            state.pending_avg = False
            state.next_avg_price = None
            return

        logger.info(f"[{symbol}] {side} Averaging order SUCCESS for level {level_str}. Waiting for FSM sync...")
        
        # 3. ДОЖИДАЕМСЯ ОБНОВЛЕНИЯ avg_entry_price ОТ ВЕБСОКЕТА
        # Предохранитель от бесконечного зависания: ждем максимум 3 секунды
        sync_success = await Utils.wait_for_fsm_sync(state, timeout_sec=3.0, poll_interval=0.01)
            
        if not sync_success:
            logger.warning(f"[{symbol}] {side} WS did not update avg_entry_price in time! Forcing REST fallback...")
            try:
                positions = await client.fetch_positions(symbol)
                for p in positions:
                    if p.get("positionSide") == side:
                        new_avg = float(p.get("entryPrice", 0.0))
                        new_vol = float(p.get("positionAmt", 0.0))
                        if new_avg > 0:
                            state.avg_entry_price = new_avg
                            state.total_volume = new_vol
                logger.info(f"[{symbol}] {side} REST fallback applied! New avg_entry_price: {state.avg_entry_price}")
            except Exception as e:
                logger.error(f"[{symbol}] {side} REST fallback failed: {e}")
        else:
            logger.info(f"[{symbol}] {side} FSM synced! New avg_entry_price: {state.avg_entry_price}")

        # 4. ПОСТАНОВКА НОВОГО ЛИМИТНОГО ТЕЙК ПРОФИТА
        await tp_manager.place_take_profit(client, symbol, side, current_price, spec_data, state)

        # Освобождаем флаги
        state.pending_avg = False
        state.next_avg_price = None
        state.next_fallback_price = None
