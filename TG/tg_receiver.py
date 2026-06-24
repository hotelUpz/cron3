# ==============================================================================
# Path: TG/tg_receiver.py
# Role: Telegram-бот для управления торговым ядром (Start/Stop, Настройки)
# ==============================================================================
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from c_log import UnifiedLogger
from consts import TG_TOKEN, ANALYTICS_DIR, TG_ALLOWED_USERS
from TG.template_manager import TemplateManager

logger = UnifiedLogger("TGReceiver")

class TGStates(StatesGroup):
    waiting_for_symbol = State()
    waiting_for_json = State()

class TelegramReceiver:
    def __init__(self, bot_core):
        self.bot_core = bot_core
        self.bot = Bot(token=TG_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.template_manager = TemplateManager()
        self._lock = asyncio.Lock()
        
        # Регистрация простого middleware для проверки прав доступа
        @self.dp.message.outer_middleware()
        async def check_user_message(handler, event: Message, data: dict):
            if TG_ALLOWED_USERS and event.from_user.id not in TG_ALLOWED_USERS:
                logger.warning(f"Unauthorized access attempt by {event.from_user.id}")
                return
            return await handler(event, data)

        @self.dp.callback_query.outer_middleware()
        async def check_user_callback(handler, event: CallbackQuery, data: dict):
            if TG_ALLOWED_USERS and event.from_user.id not in TG_ALLOWED_USERS:
                logger.warning(f"Unauthorized access attempt by {event.from_user.id}")
                return
            return await handler(event, data)

        self._register_handlers()

    def _get_main_keyboard(self):
        keyboard = [
            [
                KeyboardButton(text="▶️ Start"),
                KeyboardButton(text="⏸️ Stop")
            ],
            [
                KeyboardButton(text="📊 Analytics"),
                KeyboardButton(text="⚙️ Set Coins")
            ],
            [
                KeyboardButton(text="📜 Get Logs")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def _get_confirm_start_keyboard(self):
        keyboard = [
            [
                KeyboardButton(text="✅ Confirm Start"),
                KeyboardButton(text="⚙️ Set Coins")
            ],
            [
                KeyboardButton(text="🔙 Cancel")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def _register_handlers(self):
        @self.dp.message(Command("start"))
        async def start_cmd(message: Message, state: FSMContext):
            await state.clear()
            status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}"
            await message.answer(text, reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "▶️ Start")
        async def on_pre_start(message: Message, state: FSMContext):
            await state.clear()
            from consts import _CFG
            symbols = _CFG.get("symbols", [])
            
            banner_lines = ["<b>Подтвердите настройки запуска:</b>\n"]
            for sym in symbols:
                sym_lower = sym.lower()
                runtime_path = self.template_manager.runtime_dir / f"{sym_lower}.json"
                if runtime_path.exists():
                    import json
                    try:
                        with open(runtime_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        l_en = data.get("LONG", {}).get("enable", False)
                        l_sz = data.get("LONG", {}).get("invest_size", 0)
                        s_en = data.get("SHORT", {}).get("enable", False)
                        s_sz = data.get("SHORT", {}).get("invest_size", 0)
                        
                        banner_lines.append(f"<b>{sym}</b>:")
                        banner_lines.append(f"  LONG: {'✅ On' if l_en else '❌ Off'} ({l_sz}$)")
                        banner_lines.append(f"  SHORT: {'✅ On' if s_en else '❌ Off'} ({s_sz}$)")
                    except Exception:
                        banner_lines.append(f"<b>{sym}</b>: [Ошибка чтения конфигурации]")
                else:
                    banner_lines.append(f"<b>{sym}</b>: [Рантайм не создан]")
            
            text = "\n".join(banner_lines)
            await message.answer(text, reply_markup=self._get_confirm_start_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "🔙 Cancel")
        async def on_cancel(message: Message, state: FSMContext):
            await state.clear()
            status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}"
            await message.answer(text, reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "✅ Confirm Start")
        async def on_confirm_start(message: Message, state: FSMContext):
            await state.clear()
            if not self.bot_core.is_paused:
                await message.answer("Trading is already running!", reply_markup=self._get_main_keyboard())
                return
            self.bot_core.is_paused = False
            logger.info("[TG] User started trading loops.")
            await message.answer("<b>Control Panel</b>\nCurrent Status: ▶️ Running", reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "⏸️ Stop")
        async def on_stop_trade(message: Message, state: FSMContext):
            await state.clear()
            if self.bot_core.is_paused:
                await message.answer("Trading is already paused!", reply_markup=self._get_main_keyboard())
                return
            self.bot_core.is_paused = True
            logger.info("[TG] User stopped trading loops.")
            await message.answer("<b>Control Panel</b>\nCurrent Status: ⏸️ Paused", reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "📜 Get Logs")
        async def on_get_logs(message: Message, state: FSMContext):
            await state.clear()
            log_path = os.path.join("logs", "all.log")
            if os.path.exists(log_path):
                await message.answer_document(FSInputFile(log_path))
            else:
                await message.answer("Global log file not found.")

        @self.dp.message(F.text == "📊 Analytics")
        async def on_analytics(message: Message, state: FSMContext):
            await state.clear()
            import json
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo
            from consts import _CFG
            
            # Read JSON
            analytics_path = ANALYTICS_DIR / "analytics.json"
            if analytics_path.exists():
                text = analytics_path.read_text(encoding="utf-8")
                
                header = ""
                try:
                    data = json.loads(text)
                    ts = data.get("last_updated_ts")
                    if ts:
                        tz_str = _CFG.get("app", {}).get("time_zone", "UTC")
                        try:
                            dt = datetime.fromtimestamp(ts / 1000.0, tz=ZoneInfo(tz_str))
                        except Exception:
                            dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                        header = f"<b>ℹ️ Аналитика рассчитана по состоянию на: {time_str}</b>\n\n"
                    else:
                        header = "<b>ℹ️ Аналитика рассчитана по состоянию на: [неизвестно]</b>\n\n"
                except Exception as e:
                    logger.error(f"Error parsing analytics JSON for timestamp: {e}")

                # Telegram has message length limits, so we send it as a monospaced block or split
                if len(text) > 3800:
                    text = text[:3800] + "\n...[truncated]"
                await message.answer(f"{header}<pre>{text}</pre>", parse_mode="HTML")
            else:
                await message.answer("Analytics JSON not found in ANALYTICS_DIR.")

            # Send CSV
            csv_path = ANALYTICS_DIR / "trades_ledger.csv"
            if csv_path.exists():
                await message.answer_document(FSInputFile(str(csv_path)))
            else:
                await message.answer("Trades ledger CSV not found.")

        @self.dp.message(F.text == "⚙️ Set Coins")
        async def on_set_coins(message: Message, state: FSMContext):
            await message.answer("Пожалуйста, введите символ монеты (например: WIFUSDT):", reply_markup=self._get_confirm_start_keyboard())
            await state.set_state(TGStates.waiting_for_symbol)

        @self.dp.message(TGStates.waiting_for_symbol)
        async def process_symbol(message: Message, state: FSMContext):
            symbol = message.text.strip().upper()
            if not symbol.endswith("USDT"):
                await message.answer("Символ должен заканчиваться на USDT. Попробуйте еще раз:")
                return

            template_str = self.template_manager.generate_tg_template(symbol)
            if "error" in template_str:
                await message.answer(f"Ошибка генерации шаблона: {template_str}")
                await state.clear()
                return

            await message.answer("<b>Чистый шаблон настроек (для копирования и изменения):</b>", parse_mode="HTML")
            
            # Телеграм режет длинные сообщения, поэтому бьем на чанки если нужно
            if len(template_str) > 4000:
                await message.answer(f"<pre>{template_str[:4000]}</pre>", parse_mode="HTML")
                await message.answer(f"<pre>{template_str[4000:]}</pre>", parse_mode="HTML")
            else:
                await message.answer(f"<pre>{template_str}</pre>", parse_mode="HTML")
            
            # Теперь показываем текущее рантайм-состояние (грязный кэш)
            runtime_path = self.template_manager.runtime_dir / f"{symbol.lower()}.json"
            if runtime_path.exists():
                import json
                try:
                    with open(runtime_path, 'r', encoding='utf-8') as f:
                        rt_data = json.load(f)
                    rt_str = json.dumps(rt_data, indent=4)
                    await message.answer("<b>Текущее состояние монеты (рантайм кэш):</b>", parse_mode="HTML")
                    if len(rt_str) > 4000:
                        await message.answer(f"<pre>{rt_str[:4000]}</pre>", parse_mode="HTML")
                        await message.answer(f"<pre>{rt_str[4000:]}</pre>", parse_mode="HTML")
                    else:
                        await message.answer(f"<pre>{rt_str}</pre>", parse_mode="HTML")
                except Exception as e:
                    await message.answer(f"Ошибка чтения рантайм кэша: {e}")
            else:
                await message.answer("<i>Рантайм кэш для этой монеты еще не создан (будет создан при старте).</i>", parse_mode="HTML")

            await message.answer("Теперь отправьте отредактированный JSON с новыми настройками (он обновит конфигурацию, не трогая рантайм поля):")
            await state.update_data(symbol=symbol)
            await state.set_state(TGStates.waiting_for_json)

        @self.dp.message(TGStates.waiting_for_json)
        async def process_json(message: Message, state: FSMContext):
            json_str = message.text.strip()
            
            import json
            symbol = ""
            try:
                data = json.loads(json_str)
                symbol = data.get("symbol", "").upper()
            except Exception:
                pass
            
            async with self._lock:
                success, msg = self.template_manager.apply_tg_template(json_str)
            
            if success:
                if symbol and symbol not in self.bot_core.symbols:
                    await self.bot_core.add_symbol(symbol)
                else:
                    # Trigger RuntimeManager to reload caches for existing symbols
                    self.bot_core.runtime_manager.load_initial_caches(self.bot_core.symbols)
                    self.bot_core.runtime_configs = self.bot_core.runtime_manager.caches
                    # MUST sync the in-memory PositionState with the updated cache so price=None takes effect
                    self.bot_core.runtime_manager.populate_fsm_from_cache(self.bot_core.fsm_states)
                
                await message.answer(f"✅ {msg}")
                await state.clear()
            else:
                await message.answer(f"❌ {msg}\nПопробуйте отправить исправленный JSON еще раз.")

    async def start(self):
        logger.info("Starting Telegram Receiver...")
        await self.dp.start_polling(self.bot)
