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
    waiting_for_add_symbol = State()
    waiting_for_del_symbol = State()
    waiting_for_edit_symbol = State()
    waiting_for_edit_json = State()
    waiting_for_base_json = State()

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
                KeyboardButton(text="📜 Get Logs"),
                KeyboardButton(text="ℹ️ Status")
            ],
            [
                KeyboardButton(text="📂 Get CFG")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def _get_set_coins_keyboard(self):
        keyboard = [
            [
                KeyboardButton(text="➕ Add"),
                KeyboardButton(text="✏️ Edit"),
                KeyboardButton(text="🗑️ Del")
            ],
            [
                KeyboardButton(text="📄 _base"),
                KeyboardButton(text="❓ Help")
            ],
            [
                KeyboardButton(text="🔙 Back")
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

    def _get_cancel_keyboard(self):
        keyboard = [
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
            
            if not self.bot_core.is_paused:
                await message.answer("⚠️ Trading is already running!", reply_markup=self._get_main_keyboard())
                return
                
            from consts import _CFG
            symbols = _CFG.get("symbols", [])
            
            for sym in symbols:
                sym_lower = sym.lower()
                runtime_path = self.template_manager.runtime_dir / f"{sym_lower}.json"
                if runtime_path.exists():
                    import json
                    try:
                        with open(runtime_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        lines = [f"<b>{sym} Settings:</b>"]
                        for side in ["LONG", "SHORT"]:
                            cfg = data.get(side, {})
                            en = cfg.get("enable", False)
                            sz = cfg.get("invest_size", 0)
                            lev = cfg.get("leverage", 0)
                            margin = cfg.get("margin_type", "CROSSED")
                            
                            lines.append(f"  <b>{side}</b>: {'✅ On' if en else '❌ Off'}")
                            if en:
                                lines.append(f"    ├ Invest: {sz}$ | Lev: {lev}x | {margin}")
                                
                                grid = cfg.get("grid", {})
                                indents = []
                                for k in sorted(grid.keys(), key=lambda x: int(x)):
                                    indents.append(str(grid[k].get("indent", 0)))
                                lines.append(f"    ├ Grid: [{', '.join(indents)}]")
                                
                                tp_map = cfg.get("tp_map", {})
                                tps = []
                                for k in sorted(tp_map.keys(), key=lambda x: int(x)):
                                    tps.append(str(tp_map[k].get("indent", 0)))
                                lines.append(f"    └ TP: [{', '.join(tps)}]")
                                
                        msg_text = "\n".join(lines)
                        await message.answer(msg_text, parse_mode="HTML")
                    except Exception as e:
                        await message.answer(f"<b>{sym}</b>: [Ошибка чтения конфигурации: {e}]", parse_mode="HTML")
                else:
                    await message.answer(f"<b>{sym}</b>: [Рантайм не создан]", parse_mode="HTML")
            
            await message.answer("<b>Подтвердите настройки запуска:</b>", reply_markup=self._get_confirm_start_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "🔙 Cancel")
        async def on_cancel(message: Message, state: FSMContext):
            await state.clear()
            status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}"
            await message.answer(text, reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "✅ Confirm Start")
        async def on_confirm_start(message: Message, state: FSMContext):
            await state.clear()
            
            # Save auto_start = True to app.json
            from consts import DATA_DIR
            from c_utils import Utils
            app_json_path = DATA_DIR / "app.json"
            app_data = Utils.read_json_file(app_json_path)
            if "app" not in app_data:
                app_data["app"] = {}
            app_data["app"]["auto_start"] = True
            Utils.write_json_file(app_json_path, app_data)
            
            if not self.bot_core.is_paused:
                await message.answer("Trading is already running!", reply_markup=self._get_main_keyboard())
                return
            self.bot_core.is_paused = False
            logger.info("[TG] User started trading loops. auto_start flag saved to True.")
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

        @self.dp.message(F.text == "ℹ️ Status")
        async def on_status(message: Message, state: FSMContext):
            await state.clear()
            status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}"
            await message.answer(text, reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "📜 Get Logs")
        async def on_get_logs(message: Message, state: FSMContext):
            await state.clear()
            log_path = os.path.join("logs", "all.log")
            if os.path.exists(log_path):
                await message.answer_document(FSInputFile(log_path))
            else:
                await message.answer("Global log file not found.")

        @self.dp.message(F.text == "📂 Get CFG")
        async def on_get_cfg(message: Message, state: FSMContext):
            await state.clear()
            from consts import DATA_DIR
            from c_utils import Utils
            import json
            
            dump_data = {}
            
            # Read app.json
            app_json = DATA_DIR / "app.json"
            if app_json.exists():
                dump_data["app.json"] = Utils.read_json_file(app_json)
                
            # Read _base.json
            base_json = DATA_DIR / "_base.json"
            if base_json.exists():
                dump_data["_base.json"] = Utils.read_json_file(base_json)
                
            # Read runtimes
            dump_data["runtime"] = {}
            runtime_dir = DATA_DIR / "runtime"
            if runtime_dir.exists():
                for file_path in runtime_dir.glob("*.json"):
                    dump_data["runtime"][file_path.name] = Utils.read_json_file(file_path)
                    
            dump_path = os.path.join("logs", "all_configs.json")
            os.makedirs("logs", exist_ok=True)
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=4)
                
            await message.answer_document(FSInputFile(dump_path))

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
                        
                        help_str = (
                            "<b>📚 Analytics Cheat Sheet</b>\n"
                            "▪️ <b>roi_pct</b>: Return on Investment (%) → <i>(Cur_Balance - Start_Balance) / Start_Balance * 100</i>\n"
                            "▪️ <b>load_ratio</b>: Grid Load Ratio → <i>|Unrealized PnL| / Gross Profit</i> (Floating risk taken per 1 USDT of closed profit)\n"
                            "▪️ <b>recovery_factor</b>: Recovery Factor → <i>Gross Profit / |Max Drawdown|</i> (Can profit cover max drawdowns?)\n"
                            "▪️ <b>gross_profit_usdt</b>: Total realized profit from all closed trades (incl. commissions/funding)\n"
                            "▪️ <b>net_profit_usdt</b>: True mathematical growth → <i>Gross Profit + Unrealized PnL</i>\n"
                            "▪️ <b>unrealized_pnl_usdt</b>: Current floating drawdown of all open positions\n"
                            "▪️ <b>cur_balance_usdt</b>: Current mathematical margin balance → <i>Start Balance + Net Profit</i>\n"
                        )
                        
                        header = f"{help_str}\n<b>ℹ️ Расчет по состоянию на: {time_str}</b>\n\n"
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

            # Send CSVs
            csv_path = ANALYTICS_DIR / "trades_ledger.csv"
            if csv_path.exists():
                await message.answer_document(FSInputFile(str(csv_path)))
            else:
                await message.answer("Trades ledger CSV not found.")
                
            # Send Equity Curve Plot
            try:
                import sys
                import os
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                from ANALYTICS.plotter import generate_equity_curve
                
                plot_path = generate_equity_curve()
                if plot_path and os.path.exists(plot_path):
                    await message.answer_photo(FSInputFile(plot_path), caption="📈 График движения баланса (Equity Curve)")
            except Exception as e:
                logger.error(f"Error generating or sending equity curve: {e}")

        @self.dp.message(F.text == "⚙️ Set Coins")
        async def on_set_coins(message: Message, state: FSMContext):
            await state.clear()
            await message.answer("<b>Управление монетами:</b>\nВыберите действие в меню.", reply_markup=self._get_set_coins_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "🔙 Back")
        async def on_back_from_coins(message: Message, state: FSMContext):
            await state.clear()
            status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}"
            await message.answer(text, reply_markup=self._get_main_keyboard(), parse_mode="HTML")

        @self.dp.message(F.text == "❓ Help")
        async def on_help_coins(message: Message, state: FSMContext):
            help_text = (
                "<b>Гайд по управлению монетами:</b>\n\n"
                "➕ <b>Add</b>: Добавить новую монету. Бот возьмет шаблон из <code>_base.json</code> и сразу запустит монету в работу.\n"
                "✏️ <b>Edit</b>: Редактировать настройки запущенной монеты. Бот пришлет текущий конфиг, вы его правите и отправляете обратно.\n"
                "🗑️ <b>Del</b>: Удалить монету. Бот моментально удалит её из всех систем и перестанет следить за ней (ордера на бирже останутся).\n"
                "📄 <b>_base</b>: Отредактировать глобальный шаблон (применяется при добавлении новых монет)."
            )
            await message.answer(help_text, parse_mode="HTML")

        # =========================================================
        # ADD SYMBOL
        # =========================================================
        @self.dp.message(F.text == "➕ Add")
        async def on_add_btn(message: Message, state: FSMContext):
            await message.answer("Введите символ монеты для добавления (например: WIFUSDT):", reply_markup=self._get_cancel_keyboard())
            await state.set_state(TGStates.waiting_for_add_symbol)

        @self.dp.message(TGStates.waiting_for_add_symbol)
        async def process_add_symbol(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            symbol = message.text.strip().upper()
            if not symbol.endswith("USDT"):
                await message.answer("Символ должен заканчиваться на USDT. Попробуйте еще раз:")
                return

            # Apply base template automatically and add to BotCore
            import json
            base_data = self.template_manager.apply_tg_template(json.dumps({"symbol": symbol}))
            # Wait, apply_tg_template parses JSON, but if we don't pass full JSON it might fail or reset.
            # We need to manually construct the config or use a helper.
            # Actually, `template_manager.generate_tg_template` gets base.
            base_str = self.template_manager.generate_tg_template(symbol)
            success, msg = self.template_manager.apply_tg_template(base_str)
            
            if success:
                if symbol not in self.bot_core.symbols:
                    await self.bot_core.add_symbol(symbol)
                await message.answer(f"✅ Монета {symbol} успешно добавлена и запущена в работу на основе базового шаблона!", reply_markup=self._get_set_coins_keyboard())
                await state.clear()
            else:
                await message.answer(f"❌ Ошибка добавления: {msg}", reply_markup=self._get_set_coins_keyboard())
                await state.clear()

        # =========================================================
        # DEL SYMBOL
        # =========================================================
        @self.dp.message(F.text == "🗑️ Del")
        async def on_del_btn(message: Message, state: FSMContext):
            active_coins = ", ".join(self.bot_core.symbols)
            if not active_coins:
                active_coins = "Нет активных монет"
            await message.answer(f"Активные монеты: <b>{active_coins}</b>\n\nВведите символ монеты для УДАЛЕНИЯ (например: WIFUSDT):", parse_mode="HTML", reply_markup=self._get_cancel_keyboard())
            await state.set_state(TGStates.waiting_for_del_symbol)

        @self.dp.message(TGStates.waiting_for_del_symbol)
        async def process_del_symbol(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            symbol = message.text.strip().upper()
            if symbol not in self.bot_core.symbols:
                await message.answer(f"❌ Монета {symbol} не найдена в активных.", reply_markup=self._get_set_coins_keyboard())
                await state.clear()
                return

            await self.bot_core.delete_symbol(symbol)
            await message.answer(f"✅ Монета {symbol} успешно удалена из всех систем бота (ордера на бирже оставлены без изменений).", reply_markup=self._get_set_coins_keyboard())
            await state.clear()

        # =========================================================
        # EDIT SYMBOL
        # =========================================================
        @self.dp.message(F.text == "✏️ Edit")
        async def on_edit_btn(message: Message, state: FSMContext):
            active_coins = ", ".join(self.bot_core.symbols)
            if not active_coins:
                active_coins = "Нет активных монет"
            await message.answer(f"Активные монеты: <b>{active_coins}</b>\n\nВведите символ монеты для редактирования (например: WIFUSDT):", parse_mode="HTML", reply_markup=self._get_cancel_keyboard())
            await state.set_state(TGStates.waiting_for_edit_symbol)

        @self.dp.message(TGStates.waiting_for_edit_symbol)
        async def process_edit_symbol(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            symbol = message.text.strip().upper()
            if symbol not in self.bot_core.symbols:
                await message.answer(f"❌ Монета {symbol} не найдена в активных.")
                return

            runtime_path = self.template_manager.runtime_dir / f"{symbol.lower()}.json"
            if runtime_path.exists():
                import json
                try:
                    with open(runtime_path, 'r', encoding='utf-8') as f:
                        rt_data = json.load(f)
                    
                    # We create an editable template from runtime
                    editable = {"symbol": symbol}
                    for side in ("LONG", "SHORT"):
                        if side in rt_data:
                            editable[side] = rt_data[side]
                    
                    rt_str = json.dumps(editable, indent=4)
                    await message.answer("<b>Текущие настройки монеты (скопируйте, измените и отправьте обратно):</b>", parse_mode="HTML")
                    
                    if len(rt_str) > 4000:
                        await message.answer(f"<pre>{rt_str[:4000]}</pre>", parse_mode="HTML")
                        await message.answer(f"<pre>{rt_str[4000:]}</pre>", parse_mode="HTML")
                    else:
                        await message.answer(f"<pre>{rt_str}</pre>", parse_mode="HTML")
                        
                    await state.update_data(symbol=symbol)
                    await state.set_state(TGStates.waiting_for_edit_json)
                except Exception as e:
                    await message.answer(f"❌ Ошибка чтения конфига: {e}", reply_markup=self._get_set_coins_keyboard())
                    await state.clear()
            else:
                await message.answer("❌ Файл конфигурации не найден.", reply_markup=self._get_set_coins_keyboard())
                await state.clear()

        @self.dp.message(TGStates.waiting_for_edit_json)
        async def process_edit_json(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            json_str = message.text.strip()
            
            async with self._lock:
                success, msg = self.template_manager.apply_tg_template(json_str)
            
            if success:
                # Reload runtime caches for the bot
                self.bot_core.runtime_manager.load_initial_caches(self.bot_core.symbols)
                self.bot_core.runtime_configs = self.bot_core.runtime_manager.caches
                self.bot_core.runtime_manager.populate_fsm_from_cache(self.bot_core.fsm_states)
                
                await message.answer("✅ Настройки успешно обновлены и применены на лету!", reply_markup=self._get_set_coins_keyboard())
                await state.clear()
            else:
                await message.answer(f"❌ Ошибка: {msg}\nИсправьте JSON и отправьте снова.")

        # =========================================================
        # EDIT _BASE TEMPLATE
        # =========================================================
        @self.dp.message(F.text == "📄 _base")
        async def on_base_btn(message: Message, state: FSMContext):
            from c_utils import Utils
            base_data = Utils.read_json_file(self.template_manager.base_file)
            import json
            base_str = json.dumps(base_data, indent=4)
            await message.answer("<b>Текущий базовый шаблон _base.json (отредактируйте и отправьте обратно):</b>", reply_markup=self._get_cancel_keyboard(), parse_mode="HTML")
            await message.answer(f"<pre>{base_str}</pre>", parse_mode="HTML")
            await state.set_state(TGStates.waiting_for_base_json)

        @self.dp.message(TGStates.waiting_for_base_json)
        async def process_base_json(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            json_str = message.text.strip()
            import json
            try:
                new_base = json.loads(json_str)
                from c_utils import Utils
                Utils.write_json_file(self.template_manager.base_file, new_base)
                await message.answer("✅ Базовый шаблон успешно обновлен!", reply_markup=self._get_set_coins_keyboard())
                await state.clear()
            except Exception as e:
                await message.answer(f"❌ Ошибка JSON: {e}\nИсправьте и отправьте снова.")

    async def start(self):
        logger.info("Starting Telegram Receiver...")
        await self.dp.start_polling(self.bot)
