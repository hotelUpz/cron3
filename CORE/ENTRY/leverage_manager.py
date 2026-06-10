# ==============================================================================
# Path: CORE/leverage_manager.py
# Role: Кеширование и установка плеча и типа маржи
# ==============================================================================

from typing import Dict
from c_log import UnifiedLogger

logger = UnifiedLogger("LeverageManager")

class LeverageManager:
    def __init__(self):
        # Кэш в формате: "SYMBOL_MARGINTYPE_LEVERAGE" -> bool
        # Пример: "BTCUSDT_ISOLATED_10": True
        self._cache: Dict[str, bool] = {}

    async def set_leverage_and_margin(self, client, symbol: str, side_cfg: dict):
        """
        Извлекает настройки из side_cfg и устанавливает плечо и тип маржи для символа. 
        Скипает API вызов, если значения уже кешированы.
        """
        leverage = int(side_cfg["leverage"])
        margin_type = str(side_cfg["margin_type"]).upper()
        
        cache_key = f"{symbol}_{margin_type}_{leverage}"
        
        if self._cache.get(cache_key):
            # Уже установлено в этом рантайме
            return
        
        # Установка типа маржи
        margin_res = await client.set_margin_type(symbol, margin_type)
        if not margin_res.success:
            # Binance возвращает ошибку, если тип маржи уже установлен (No need to change margin type.)
            # Это можно игнорировать как ошибку, но запишем лог
            if margin_res.msg and "No need to change" in margin_res.msg:
                logger.debug(f"[{symbol}] Margin type {margin_type} is already set on exchange.")
            else:
                logger.warning(f"[{symbol}] Failed to set margin type {margin_type}: {margin_res.msg}")
                
        # Установка плеча
        leverage_res = await client.set_leverage(symbol, leverage)
        if not leverage_res.success:
            logger.error(f"[{symbol}] Failed to set leverage {leverage}: {leverage_res.msg}")
        else:
            logger.info(f"[{symbol}] Successfully set leverage to {leverage} and margin type to {margin_type}")
            # Кешируем успешную установку
            self._cache[cache_key] = True
