# ==============================================================================
# Path: CORE/TP/fallback_tp_manager.py
# Role: Менеджер страховочного тейк-профита (Fallback Market Hit)
# ==============================================================================

from c_log import UnifiedLogger
from CORE._utils import TradeMath, RiskCalculatingUtils

logger = UnifiedLogger("FallbackMarketTP")

class FallbackTpManager:
    def __init__(self):
        pass

    async def process(self, client, runtime_manager, symbol: str, side: str, state, current_price: float, spec_data: dict):
        """Проверяет пробитие страховочной цены (Fallback TP) и бьет по рынку."""
        if not state.in_position or state.is_finished or current_price is None:
            return

        # Предохранитель от гонок: если уже летит маркет-ордер фолбека
        if state.pending_rolling_tp:
            return

        # 1. Детерминация цены фолбека (кешируем только прайс для горячего пути)
        if state.fallback_price is None:
            if state.avg_entry_price <= 0:
                return # Ждем пока сенсоры синхронизируют цену входа
            
            tp_map = state.tp_map
            current_level = state.current_grid_level
            
            if current_level not in tp_map:
                return
                
            fallback_indent_pct = tp_map[current_level]["fallback_indent"]
            fb_price = TradeMath.calculate_take_profit_price(
                state.avg_entry_price, fallback_indent_pct, side, spec_data, symbol
            )
            state.fallback_price = fb_price

        # 2. Горячий путь (O(1) сравнение)
        triggered = False
        if side == "LONG" and current_price >= state.fallback_price:
            triggered = True
        elif side == "SHORT" and current_price <= state.fallback_price:
            triggered = True

        if triggered:
            # Предохранитель от повторного срабатывания (чтоб 100 раз не переебнуться)
            state.pending_rolling_tp = True
            
            volume_float = abs(state.total_volume)
            volume = TradeMath.round_qty(volume_float, spec_data, symbol)
            order_side = "SELL" if side == "LONG" else "BUY"

            logger.warning(f"[{symbol}] {side} FALLBACK MARKET TRIGGERED! Price {current_price} crossed {state.fallback_price}. Closing all.")
            
            res = await client.make_order(
                symbol=symbol,
                qty=volume,
                side=order_side,
                position_side=side,
                market_type="MARKET"
            )

            if res.success:
                logger.info(f"[{symbol}] Fallback Market Order successfully executed.")
                state.is_finished = True  # Только теперь говорим оркестратору, что всё
            else:
                logger.error(f"[{symbol}] Failed to execute Fallback Market Order: {res.error_msg}")
            
            state.pending_rolling_tp = False  # Снимаем блокировку
