# ==============================================================================
# Path: CORE/tp_manager.py
# Role: Менеджер постановки лимитных тейк-профит ордеров
# ==============================================================================

from c_log import UnifiedLogger
from CORE._utils import TradeMath

logger = UnifiedLogger("TakeProfitManager")

class TakeProfitManager:
    def __init__(self, runtime_manager):
        self.runtime_manager = runtime_manager

    async def place_take_profit(self, client, symbol: str, side: str, side_cfg: dict, current_price: float, spec_data: dict, state, volume: float = None):
        """Расчет и постановка лимитного TP ордера."""
        from CORE._utils import RiskCalculatingUtils
        
        grid = side_cfg["grid"]
        current_level_str = RiskCalculatingUtils.get_current_grid_level(grid)
        
        tp_map = side_cfg["tp_map"]
        current_tp = tp_map[current_level_str]
        tp_indent = current_tp["indent"]
        
        # Расчет цены TP
        tp_price = TradeMath.calculate_take_profit_price(current_price, tp_indent, side, spec_data, symbol)
        
        # Всегда продаем весь накопленный объем (если volume не передан явно)
        if volume is None:
            volume_float = abs(state.total_volume)
            volume = TradeMath.round_qty(volume_float, spec_data, symbol)
        
        # Сторона ордера: обратная стороне позиции
        order_side = "SELL" if side == "LONG" else "BUY"
        
        logger.info(f"[{symbol}] Placing {side} take profit limit order at {tp_price}. Vol: {volume}")
        res = await client.make_order(
            symbol=symbol,
            qty=volume,
            side=order_side,
            position_side=side,
            market_type="LIMIT",
            price=tp_price
        )
        
        if res.success and res.data:
            order_id = res.data.get("orderId")
            if order_id:
                logger.info(f"[{symbol}] TP order successfully placed. ID: {order_id}")
                
                # Фиксируем ID в рантайме
                self.runtime_manager.caches[symbol][side]["tp_id"] = order_id
                
                # Помечаем tp_map текущий уровень как активный
                if "tp_map" not in self.runtime_manager.caches[symbol][side]:
                    self.runtime_manager.caches[symbol][side]["tp_map"] = {current_level_str: {}}
                    
                self.runtime_manager.caches[symbol][side]["tp_map"][current_level_str]["is_active"] = True
                self.runtime_manager.caches[symbol][side]["tp_map"][current_level_str]["price"] = tp_price
                
                await self.runtime_manager.save_cache(symbol)
                return True
                
        logger.error(f"[{symbol}] Failed to place TP for {side}: {res.msg}")
        return False
