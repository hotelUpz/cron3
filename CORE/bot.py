# ==============================================================================
# Path: CORE/bot.py
# Role: Торговое ядро и основная логика
# ==============================================================================

import asyncio
import logging
import os
import time
from pathlib import Path

from consts import _CFG, DATA_DIR, TIME_SLACK_SEC, SPEC_TTL_SEC
from API.BINANCE.public import BinancePublic
from API.BINANCE.price_stream import BinanceHotPriceStream, HotPriceTick
from CORE.ENTRY.signal import TimeControl
from CORE.ENTRY.leverage_manager import LeverageManager
from CORE._utils import TradeMath
from API.BINANCE.client import BinanceClient
from POS_FSM.models import PositionState
from c_utils import Utils

logger = logging.getLogger(__name__)

class BotCore:
    def __init__(self):
        self.is_running = False
        # Работаем только с теми символами, которые прописаны в конфигах .app.json в разделе symbols
        self.symbols = _CFG.get("symbols", [])
        self.prices = {}   # Структура для хранения цен
        from RUNTIME_FSM.runtime_manager import RuntimeFsmManager
        self.runtime_manager = RuntimeFsmManager()
        self.runtime_configs = self.runtime_manager.caches # Кеш рантаймов
        
        # Флаги готовности стримов
        self.price_stream_synced = asyncio.Event()
        self.pos_stream_synced = asyncio.Event()
        
        # Получаем таймфрейм из конфига app.json (секция signal)
        signal_cfg = _CFG.get("signal", {})
        timeframe = signal_cfg.get("timeframe", "5m")
        self.time_control = TimeControl(interval=timeframe)
        
        # 2. Менеджеры
        from CORE.ENTRY.leverage_manager import LeverageManager
        self.leverage_manager = LeverageManager()
        
        from CORE.TP.tp_manager import TakeProfitManager
        self.tp_manager = TakeProfitManager(self.runtime_manager)
        
        from CORE.GRID.avg_manager import AverageManager
        self.avg_manager = AverageManager()
        
        from CORE.TP.fallback_tp_manager import FallbackTpManager
        self.fallback_tp_manager = FallbackTpManager()
        
        from analytics import AnalyticsManager
        self.analytics = AnalyticsManager()
        
        self.spec_data = {}
        
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.client = BinanceClient(api_key=api_key, api_secret=api_secret)
        
        # Кеш FSM-состояний в формате {symbol: {"LONG": PositionState, "SHORT": PositionState}}
        self.fsm_states = {}
        
        # Сетевые адаптеры и стримы
        self.price_stream = BinanceHotPriceStream(self.symbols)

    async def _specification_task(self):
        """Фоновая задача: Обновление спецификации."""
        try:
            while self.is_running:
                data = await BinancePublic.get_instruments()
                if data:
                    self.spec_data = {"symbols": data}
                    logger.debug("Specification updated.")
                await asyncio.sleep(SPEC_TTL_SEC) 
        except asyncio.CancelledError:
            pass
            
    async def _on_tick(self, tick: HotPriceTick):
        """Коллбэк для стрима горячих цен."""
        self.prices[tick.symbol] = tick.price
        if not self.price_stream_synced.is_set():
            self.price_stream_synced.set()

    async def _process_signal(self, symbol: str, side: str, side_cfg: dict, current_price: float, concurrent_mode: bool = False):
        """Обработка сигнала входа для символа и стороны."""
        logger.info(f"[{symbol}] Signal triggered for {side}.")
        
        # 1. Установка плеча и маржи
        await self.leverage_manager.set_leverage_and_margin(self.client, symbol, side_cfg)

        # 1.5. Открытие позиции по маркету
        invest_size = side_cfg["invest_size"]
        grid_0 = side_cfg["grid"]["0"]
        volume_pct = grid_0["volume"]
        from CORE._utils import TradeMath
        volume = TradeMath.calculate_order_volume(invest_size, volume_pct, current_price, self.spec_data, symbol)
        
        order_side = "BUY" if side == "LONG" else "SELL"
        
        logger.info(f"[{symbol}] Opening {side} market order. Volume: {volume}")
        res = await self.client.make_order(
            symbol=symbol,
            qty=volume,
            side=order_side,
            position_side=side,
            market_type="MARKET",
            concurrent_mode=concurrent_mode
        )
        if not res.success:
            logger.error(f"[{symbol}] Failed to open {side} position: {res.msg}")
            return
            
        current_time_ms = int(time.time() * 1000)
        self.fsm_states[symbol][side].open_time = current_time_ms
        side_cfg["open_time"] = current_time_ms
        await self.runtime_manager.save_cache(symbol)

        # 2. Математика расчета объема и TP
        await self.tp_manager.place_take_profit(self.client, symbol, side, current_price, self.spec_data, self.fsm_states[symbol][side], volume=volume)

    async def _check_and_reset_finished_positions(self, symbol: str, states: dict, runtime_cfg: dict):
        """Проверяет флаги is_finished, пишет аналитику, отменяет ордера и сбрасывает рантайм.""" 
        # не вижу сброса PositionState
        sides_to_reset = []
        for side in ("LONG", "SHORT"):
            if states[side].is_finished:
                sides_to_reset.append(side)

        if sides_to_reset:
            for idx, side in enumerate(sides_to_reset):
                logger.info(f"[{symbol}] {side} is_finished. Running analytics and resetting runtime cache...")
                
                # Вызов аналитики
                open_time = runtime_cfg.get(side, {}).get("open_time", 0)
                close_time = int(time.time() * 1000)
                self.analytics.record_finished_position(self.client, symbol, side, open_time, close_time)
                # Снимаем все тейк-профит ордера этой стороны
                logger.info(f"[{symbol}] {side} Canceling all limit orders for this side")
                await self.client.cancel_orders_for_side(symbol, side)
                
                # Сбрасываем рантайм-кеш в памяти и восстанавливаем стейт до дефолта
                self.runtime_manager.reset_state_to_default(symbol, side, states[side])
                
                # Сбрасываем флаг калькуляции сетки в avg_manager
                self.avg_manager.reset(symbol, side)
                
                # Если позиций две, то сбрасываем их с задержкой, чтобы биржа не забанила
                if idx < len(sides_to_reset) - 1:
                    await asyncio.sleep(0.1)

            # Сохраняем рантайм (сразу за обе стороны, если их было две)
            await self.runtime_manager.save_cache(symbol)

    async def _game_loop(self):
        """Главный цикл торгового ядра."""
        self.is_running = True
        
        # ШАГ 1. Сборка и проверка рантайм кешей (создание отсутствующих JSON)
        from RUNTIME_FSM.runtime_builder import build_runtime_caches, prompt_runtime_check
        build_runtime_caches()
        prompt_runtime_check()
        
        self.runtime_manager.load_initial_caches(self.symbols)
        self.runtime_configs = self.runtime_manager.caches

        # ШАГ 2. Инициализация стримов и фоновых задач
        spec_task = asyncio.create_task(self._specification_task())
        price_task = asyncio.create_task(self.price_stream.run(self._on_tick))
        
        from POS_FSM.pos_stream_monitor import PositionMonitor
        from POS_FSM.pos_stream import PositionStream
        
        self.pos_monitor = PositionMonitor(states_cache=self.fsm_states, target_symbols=self.symbols)
        
        # ПОДЧИНЯЕМ PositionState загруженному рантайм-кешу
        self.runtime_manager.populate_fsm_from_cache(self.fsm_states)
        
        api_key = os.getenv("BINANCE_API_KEY", "")
        self.pos_stream = PositionStream(
            api_key=api_key,
            stop_flag=lambda: not self.is_running,
            monitor=self.pos_monitor,
            target_symbols=set(self.symbols)
        )
        pos_task = asyncio.create_task(self.pos_stream.start())
        
        logger.info("Main _game_loop started. Specifications and price streams are running.")
        
        # Ожидание готовности прайс-стримов
        logger.info("Waiting for price streams to sync...")
        await self.price_stream_synced.wait()
        
        # Строгая гарантия: забираем начальный стейт позиций по REST
        await self.pos_monitor.sync_from_rest(self.client, self.symbols)
        
        # ШАГ 3. Синхронизация рантаймов с реальностью FSM
        logger.info("Streams and REST synced! Running initial RuntimeFSM Sync...")
        await self.runtime_manager.sync_with_fsm(self.fsm_states)

        while self.is_running:
            try:
                
                # # ===== ОПОРНАЯ ТОЧКА ДЛЯ ТЕСТИРОВАНИЯ =====               
                # logger.info(f"DEBUG LOOP: Prices snapshot: {list(self.prices.items())[:3]}...")
                # # Скипаем дальнейший проход для отладкыи
                # await asyncio.sleep(TIME_SLACK_SEC)
                # # continue
                # ==========================================

                # Источник сигнала для позиции, которая не в позиции
                is_signal = self.time_control.is_new_interval()

                for symbol in self.symbols:
                    runtime_cfg = self.runtime_configs.get(symbol, {})
                    states = self.fsm_states[symbol]
                    current_price = self.prices.get(symbol)
                    
                    needs_save = False
                    
                    signal_tasks = []
                    
                    # Предварительно определяем, будут ли открыты обе стороны
                    sides_to_open = []
                    for side in ("LONG", "SHORT"):
                        state = states[side]
                        side_cfg = runtime_cfg.get(side)
                        if side_cfg and side_cfg.get("enable") and not state.in_position and not state.in_position_papper:
                            sides_to_open.append(side)

                    is_concurrent = len(sides_to_open) > 1
                    
                    for side in ("LONG", "SHORT"):
                        state = states[side]
                        side_cfg = runtime_cfg.get(side)
                        
                        if not side_cfg or not side_cfg.get("enable"):
                            continue
                        
                        if not state.in_position and not state.in_position_papper:
                            if is_signal:
                                # Ставим временный флаг идемпотентности
                                state.in_position_papper = True
                                signal_tasks.append(self._process_signal(symbol, side, side_cfg, current_price, concurrent_mode=is_concurrent))
                        else:
                            # Позиция уже открыта (или в процессе in_position_papper)
                            await self.avg_manager.process(self.client, self.runtime_manager, symbol, side, state, current_price, self.spec_data, self.tp_manager)
                            await self.fallback_tp_manager.process(self.client, self.runtime_manager, symbol, side, state, current_price, self.spec_data)

                    if signal_tasks:
                        await asyncio.gather(*signal_tasks)

                    # В конце итерации по символу проверяем закрытие позиций
                    await self._check_and_reset_finished_positions(symbol, states, runtime_cfg)
                
                # Синхронизация рантаймов при изменениях в PositionState (постоянный контроль)
                await self.runtime_manager.sync_with_fsm(self.fsm_states)

                # Предотвращение блокировки event loop
                await asyncio.sleep(TIME_SLACK_SEC)

            except asyncio.CancelledError:
                logger.info("_game_loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in _game_loop: {e}", exc_info=True)
                await asyncio.sleep(TIME_SLACK_SEC)
                
        self.is_running = False
        spec_task.cancel()
        self.price_stream.stop()
        price_task.cancel()
        # Попытка быстрого сохранения стейтов при нормальном завершении
        await self.runtime_manager.sync_with_fsm(self.fsm_states, force_save=True)
        await self.client.shutdown()
        await asyncio.gather(spec_task, price_task, return_exceptions=True)

    async def start(self):
        """Запуск бота."""
        await self._game_loop()

    def stop(self):
        """Остановка бота."""
        self.is_running = False

    async def shutdown(self):
        """Гарантированное сохранение рантайма (последний чих) и закрытие сессий."""
        logger.info("Executing graceful BotCore shutdown...")
        self.is_running = False
        try:
            # Принудительно дампим стейты
            if hasattr(self, 'fsm_states') and hasattr(self, 'runtime_manager'):
                await self.runtime_manager.sync_with_fsm(self.fsm_states, force_save=True)
                logger.info("Final FSM snapshot saved to runtime cache.")
        except Exception as e:
            logger.error(f"Error saving FSM snapshot during shutdown: {e}")
            
        try:
            if hasattr(self, 'client'):
                await self.client.shutdown()
        except Exception:
            pass
