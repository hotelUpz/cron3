# ==============================================================================
# Path: RUNTIME_FSM/runtime_manager.py
# Role: Менеджер рантайм-кешей и их синхронизации с состоянием позиций
# ==============================================================================

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from consts import DATA_DIR
from c_log import UnifiedLogger
from c_utils import Utils

logger = UnifiedLogger("RuntimeManager")
RUNTIME_DIR = DATA_DIR / "runtime"

class RuntimeFsmManager:
    """
    Менеджер для управления рантайм-кешами.
    """
    def __init__(self):
        self.caches: Dict[str, Dict[str, Any]] = {}
        self.locks: Dict[str, asyncio.Lock] = {}

    def load_initial_caches(self, symbols: List[str]):
        """
        Изначально грузим и фиксируем кеш рантайма "как есть" (as is).
        """
        for sym in symbols:
            sym_lower = sym.lower()
            path = RUNTIME_DIR / f"{sym_lower}.json"
            if path.exists():
                self.caches[sym] = Utils.read_json_file(path)
            else:
                self.caches[sym] = {}
            
            if sym not in self.locks:
                self.locks[sym] = asyncio.Lock()
                
    # =========================================================================
    # СИНХРОНИЗАЦИЯ ПОСЛЕ ЗАПУСКА СТРИМА И СНЕПШОТОВ
    # =========================================================================

    async def sync_with_fsm(self, fsm_states: dict):
        """
        Метод-синхронизатор. Вызывается из BotCore ПОСЛЕ того, как мы получили 
        актуальный слепок позиций с биржи (через REST или стрим).
        Приводит json-кеш в соответствие с суровой реальностью биржи.
        """
        for symbol, cache in self.caches.items():
            sym_states = fsm_states.get(symbol, {})
            needs_save = False
            
            for side in ("LONG", "SHORT"):
                state = sym_states.get(side)
                if not state:
                    continue
                
                side_cache = cache.get(side, {})
                grid = side_cache.get("grid", {})
                grid_0 = grid.get("0", {})
                
                # Случай А: Биржа говорит, что позиции нет, а рантайм верит, что есть.
                if not state.in_position and grid_0.get("is_active"):
                    logger.warning(f"[{symbol}] {side} SYNC: На бирже позиции НЕТ, а в кеше висит 'is_active'. Сбрасываем рантайм...")
                    self.reset_side_to_default(symbol, side)
                    needs_save = True
                
                # Случай Б: На бирже позиция ЕСТЬ, а рантайм не в курсе.
                elif state.in_position and not grid_0.get("is_active"):
                    logger.warning(f"[{symbol}] {side} SYNC: На бирже позиция ЕСТЬ, а в кеше она не активна. Синхронизируем...")
                    if "grid" not in self.caches[symbol][side]:
                        self.caches[symbol][side]["grid"] = {"0": {}}
                    self.caches[symbol][side]["grid"]["0"]["is_active"] = True
                    self.caches[symbol][side]["grid"]["0"]["price"] = state.avg_entry_price
                    needs_save = True
                    
            if needs_save:
                await self.save_cache(symbol)

    def reset_side_to_default(self, symbol: str, side: str):
        """
        Сбрасывает конфигурацию конкретной стороны для монеты до дефолтной из _base.json.
        Вызывается при закрытии позиции (обнаружено по стриму) или из торговой лупы при is_finished == True.
        """
        base_file = DATA_DIR / "temp" / "_base.json"
        base_data = Utils.read_json_file(base_file)
        if not base_data or side not in base_data:
            logger.error(f"Cannot reset {symbol} {side}: _base.json is invalid.")
            return

        if symbol not in self.caches:
            self.caches[symbol] = {}
        
        # Глубоко копируем дефолтную сторону
        side_default = json.loads(json.dumps(base_data[side]))
        
        # Сбрасываем динамические флаги
        if "grid" in side_default:
            for _, grid_cfg in side_default["grid"].items():
                grid_cfg["is_active"] = False
                grid_cfg["price"] = None
                
        if "tp_map" in side_default:
            for _, tp_cfg in side_default["tp_map"].items():
                tp_cfg["is_active"] = False
                tp_cfg["price"] = None
        else:
            logger.error(f"[CRITICAL] Секция 'tp_map' ОТСУТСТВУЕТ для {side} при сбросе кеша!")

        side_default["tp_id"] = None
        side_default["open_time"] = 0

        self.caches[symbol][side] = side_default
        logger.debug(f"[{symbol}] {side} runtime cache reset to default.")

    async def save_cache(self, symbol: str):
        """Конкурентно-безопасное сохранение in-memory кеша на диск."""
        if symbol not in self.locks:
            self.locks[symbol] = asyncio.Lock()
            
        async with self.locks[symbol]:
            if symbol in self.caches:
                sym_lower = symbol.lower()
                path = RUNTIME_DIR / f"{sym_lower}.json"
                # Используем Utils для записи
                Utils.write_json_file(path, self.caches[symbol])
