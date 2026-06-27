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
    waiting_for_advanced_json = State()
    waiting_for_initial_balance = State()
    waiting_for_reset_confirm = State()

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
                KeyboardButton(text="📂 Get CFG"),
                KeyboardButton(text="🔧 Advanced")
            ],
            [
                KeyboardButton(text="💰 Задать нач. баланс"),
                KeyboardButton(text="🗑️ Сбросить аналитику")
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
                                super_indents = []
                                for k in sorted(grid.keys(), key=lambda x: int(x)):
                                    indents.append(str(grid[k].get("indent", 0)))
                                    si = grid[k].get("super_indent")
                                    super_indents.append(str(si) if si is not None else "-")
                                lines.append(f"    ├ Grid: [{', '.join(indents)}]")
                                
                                from consts import _CFG
                                if _CFG.get("advanced", {}).get("enabled", False) and any(si != "-" for si in super_indents):
                                    lines.append(f"    ├ Super: [{', '.join(super_indents)}]")
                                    
                                
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
            from consts import _CFG
            adv_enabled = _CFG.get("advanced", {}).get("enabled", False)
            adv_status = "✅ On" if adv_enabled else "❌ Off"
            text = f"<b>Control Panel</b>\nCurrent Status: {status}\nAdvanced (Volatility): {adv_status}"
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

        @self.dp.message(F.text == "🗑️ Сбросить аналитику")
        async def on_reset_analytics(message: Message, state: FSMContext):
            await state.clear()
            await message.answer("⚠️ Вы уверены, что хотите полностью удалить историю аналитики?\n\nВведите слово <b>СБРОС</b> для подтверждения или нажмите Cancel для отмены.", reply_markup=self._get_cancel_keyboard(), parse_mode="HTML")
            await state.set_state(TGStates.waiting_for_reset_confirm)

        @self.dp.message(TGStates.waiting_for_reset_confirm)
        async def process_reset_analytics_confirm(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                await state.clear()
                await message.answer("Сброс аналитики отменен.", reply_markup=self._get_main_keyboard())
                return
                
            if message.text.strip().upper() == "СБРОС":
                await state.clear()
                analytics_path = ANALYTICS_DIR / "analytics.json"
                if analytics_path.exists():
                    try:
                        os.remove(analytics_path)
                        csv_path = ANALYTICS_DIR / "trades_ledger.csv"
                        if csv_path.exists():
                            os.remove(csv_path)
                        await message.answer("✅ Файл аналитики успешно удален. Он будет создан заново при следующем обновлении.", reply_markup=self._get_main_keyboard())
                    except Exception as e:
                        await message.answer(f"❌ Ошибка при удалении файла аналитики: {e}", reply_markup=self._get_main_keyboard())
                else:
                    await message.answer("⚠️ Файл аналитики не найден.", reply_markup=self._get_main_keyboard())
            else:
                await message.answer("❌ Неверное слово подтверждения. Введите <b>СБРОС</b> или нажмите Cancel.", parse_mode="HTML")
        @self.dp.message(F.text == "💰 Задать нач. баланс")
        async def on_set_initial_balance(message: Message, state: FSMContext):
            await state.clear()
            await message.answer("Введите новый начальный баланс (start_balance_usdt) в USDT (например, 100.5):", reply_markup=self._get_cancel_keyboard())
            await state.set_state(TGStates.waiting_for_initial_balance)

        @self.dp.message(TGStates.waiting_for_initial_balance)
        async def process_initial_balance(message: Message, state: FSMContext):
            if message.text == "🔙 Cancel":
                await state.clear()
                await message.answer("Действие отменено.", reply_markup=self._get_main_keyboard())
                return
                
            try:
                new_balance = float(message.text.replace(',', '.'))
                if new_balance < 0:
                    raise ValueError("Баланс не может быть отрицательным.")
            except ValueError:
                await message.answer("❌ Некорректное число. Введите баланс еще раз (например, 100.5) или нажмите Cancel:")
                return
                
            import json
            analytics_path = ANALYTICS_DIR / "analytics.json"
            if analytics_path.exists():
                try:
                    with open(analytics_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    data["start_balance_usdt"] = round(new_balance, 4)
                    
                    # При сбросе баланса также сбрасываем пики и просадки, 
                    # чтобы не было искусственной просадки на разницу балансов
                    data["peak_balance_usdt"] = round(new_balance, 4)
                    data["_current_trough_usdt"] = round(new_balance, 4)
                    data["min_balance_usdt"] = round(new_balance, 4)
                    data["max_drawdown_usdt"] = 0.0
                    data["performance_usdt"] = 0.0
                    data["recovery_factor"] = 0.0
                    data["roi_pct"] = 0.0
                    

                    with open(analytics_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                        
                    await message.answer(f"✅ Начальный баланс успешно установлен на {new_balance} USDT.", reply_markup=self._get_main_keyboard())
                except Exception as e:
                    await message.answer(f"❌ Ошибка обновления файла аналитики: {e}", reply_markup=self._get_main_keyboard())
            else:
                await message.answer("⚠️ Файл аналитики пока не существует. Подождите, пока бот создаст его.", reply_markup=self._get_main_keyboard())
                
            await state.clear()

        @self.dp.message(F.text == "📊 Analytics")
        async def on_analytics(message: Message, state: FSMContext):
            await state.clear()
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌍 Общая аналитика", callback_data="analytics_global")],
                [InlineKeyboardButton(text="🪙 Аналитика по монете", callback_data="analytics_coin_menu")],
                [InlineKeyboardButton(text="📈 График баланса", callback_data="analytics_balance_chart")]
            ])
            await message.answer("Выберите режим аналитики:", reply_markup=keyboard)

        @self.dp.callback_query(F.data == "analytics_global")
        async def process_analytics_global(callback: CallbackQuery, state: FSMContext):
            await callback.answer()
            message = callback.message
            
            import json
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo
            from consts import _CFG
            
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
                            "<b>📚 Analytics Cheat Sheet (Global)</b>\n"
                            "▪️ <b>roi_pct</b>: Return on Investment (%) → <i>(Cur_Balance - Start_Balance) / Start_Balance * 100</i>\n"
                            "▪️ <b>load_ratio</b>: Grid Load Ratio → <i>|Unrealized PnL| / Gross Profit</i>\n"
                            "▪️ <b>recovery_factor</b>: Recovery Factor → <i>Gross Profit / |Max Drawdown|</i>\n"
                            "▪️ <b>gross_profit_usdt</b>: Total realized profit from all closed trades\n"
                            "▪️ <b>net_profit_usdt</b>: True mathematical growth → <i>Gross Profit + Unrealized PnL</i>\n"
                            "▪️ <b>cur_balance_usdt</b>: Current margin balance → <i>Start Balance + Net Profit</i>\n\n"
                            "<b>🪙 Per-Coin Metrics</b>\n"
                            "▪️ <b>avg_daily_profit</b>: Average profit per active day of trading\n"
                            "▪️ <b>max_position_size</b>: Max historical margin size actually reached (real size)\n"
                            "▪️ <b>risk_reward_ratio</b>: <i>|Max Drawdown| / Avg Daily Profit</i>\n"
                            "▪️ <b>DRME</b> (Daily Return on Max Exposure): <i>Avg Daily Profit / Max Position Size</i>\n"
                            "▪️ <b>MDME</b> (Max Drawdown on Max Exposure): <i>|Max Drawdown| / Max Position Size</i>\n"
                            "▪️ <b>max_drawdown</b> / <b>min_drawdown</b>: Max/Min historical floating drawdowns\n"
                        )
                        
                        header = f"{help_str}\n<b>ℹ️ Расчет по состоянию на: {time_str}</b>\n\n"
                    else:
                        header = "<b>ℹ️ Аналитика рассчитана по состоянию на: [неизвестно]</b>\n\n"
                except Exception as e:
                    logger.error(f"Error parsing analytics JSON for timestamp: {e}")

                # Send header first
                await message.answer(header, parse_mode="HTML")
                
                # Format JSON into beautiful text
                try:
                    data = json.loads(text)
                    
                    # Global Metrics
                    msg = "<b>🌍 GLOBAL ANALYTICS</b>\n\n"
                    
                    msg += "<b>💰 Balances:</b>\n"
                    msg += f"▪️ Start: <b>{data.get('start_balance_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Current: <b>{data.get('cur_balance_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Peak: <b>{data.get('peak_balance_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Min (Bottom): <b>{data.get('min_balance_usdt', 0)}</b> USDT\n\n"
                    
                    msg += "<b>📈 Performance:</b>\n"
                    msg += f"▪️ Net Profit: <b>{data.get('net_profit_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Gross Profit: <b>{data.get('gross_profit_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Total Commission: <b>{data.get('total_commission_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Total Funding: <b>{data.get('total_funding_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Unrealized PnL: <b>{data.get('unrealized_pnl_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Max Drawdown: <b>{data.get('max_drawdown_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ Performance (Peak-Start): <b>{data.get('performance_usdt', 0)}</b> USDT\n"
                    msg += f"▪️ ROI: <b>{data.get('roi_pct', 0)}%</b>\n"
                    msg += f"▪️ Load Ratio: <b>{data.get('load_ratio', 0)}</b>\n"
                    msg += f"▪️ Recovery Factor: <b>{data.get('recovery_factor', 0)}</b>\n"
                    msg += f"▪️ Trades: <b>{data.get('total_trades', 0)}</b> (Wins: <b>{data.get('winning_trades', 0)}</b> | <b>{data.get('winrate_pct', 0)}%</b>)\n\n"
                    
                    # Send formatted text in chunks if needed
                    await message.answer(msg, parse_mode="HTML")
                    
                    # Per-Coin Metrics
                    if "per_coin" in data and data["per_coin"]:
                        msg_coins = "<b>🪙 PER-COIN METRICS</b>\n\n"
                        for coin, cdata in data["per_coin"].items():
                            msg_coins += f"🔹 <b>{coin}</b>\n"
                            msg_coins += f"  • Trades: <b>{cdata.get('total_trades', 0)}</b> (Wins: <b>{cdata.get('winning_trades', 0)}</b> | <b>{cdata.get('winrate_pct', 0)}%</b>)\n"
                            msg_coins += f"  • Net Profit: <b>{cdata.get('net_profit_usdt', 0)}</b> USDT\n"
                            msg_coins += f"  • Profit Range: Max <b>{cdata.get('max_net_profit', 0)}</b> / Min <b>{cdata.get('min_net_profit', 0)}</b>\n"
                            msg_coins += f"  • Fees: Comm <b>{cdata.get('commission_usdt', 0)}</b> / Fund <b>{cdata.get('funding_usdt', 0)}</b>\n"
                            msg_coins += f"  • Drawdown: Cur <b>{cdata.get('current_drawdown', 0)}</b> / Max <b>{cdata.get('max_drawdown', 0)}</b> / Min <b>{cdata.get('min_drawdown', 0)}</b>\n"
                            msg_coins += f"  • Avg Daily Profit: <b>{cdata.get('avg_daily_profit', 0)}</b> USDT\n"
                            msg_coins += f"  • Max Position Size: <b>{cdata.get('max_position_size', 0)}</b> USDT\n"
                            msg_coins += f"  • Risk/Reward: <b>{cdata.get('risk_reward_ratio', 0)}</b>\n"
                            msg_coins += f"  • DRME: <b>{cdata.get('DRME', 0)}</b> | MDME: <b>{cdata.get('MDME', 0)}</b>\n\n"
                            
                        # Split coins into chunks to avoid length limits
                        max_chunk = 3900
                        if len(msg_coins) > max_chunk:
                            for i in range(0, len(msg_coins), max_chunk):
                                await message.answer(msg_coins[i:i+max_chunk], parse_mode="HTML")
                        else:
                            await message.answer(msg_coins, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error formatting analytics text: {e}")
                    await message.answer("Error formatting analytics data.")
            else:
                await message.answer("Analytics JSON not found in ANALYTICS_DIR.")

            csv_path = ANALYTICS_DIR / "trades_ledger.csv"
            if csv_path.exists():
                await message.answer_document(FSInputFile(str(csv_path)))
            else:
                await message.answer("Trades ledger CSV not found.")
                
                # Send Equity Curve
                try:
                    from ANALYTICS.plotter import generate_equity_curve
                    plot_path = generate_equity_curve()
                    if plot_path and os.path.exists(plot_path):
                        await message.answer_photo(FSInputFile(plot_path), caption="📈 График движения баланса (Equity Curve)")
                except Exception as e:
                    logger.error(f"Error generating or sending equity curve: {e}")

        @self.dp.callback_query(F.data == "analytics_balance_chart")
        async def process_analytics_balance_chart(callback: CallbackQuery, state: FSMContext):
            await callback.answer()
            message = callback.message
            try:
                from ANALYTICS.plotter import generate_equity_curve
                plot_path = generate_equity_curve()
                if plot_path and os.path.exists(plot_path):
                    await message.answer_photo(FSInputFile(plot_path), caption="📈 График движения баланса (Equity Curve)")
                else:
                    await message.answer("❌ Не удалось сгенерировать график баланса.")
            except Exception as e:
                logger.error(f"Error generating balance chart: {e}")
                await message.answer(f"❌ Ошибка генерации графика: {e}")

        @self.dp.callback_query(F.data == "analytics_coin_menu")
        async def process_analytics_coin_menu(callback: CallbackQuery, state: FSMContext):
            await callback.answer()
            message = callback.message
            
            coins = list(self.bot_core.symbols)
            if not coins:
                await message.answer("❌ Нет активных монет для аналитики.")
                return
                
            keyboard_buttons = []
            for coin in coins:
                keyboard_buttons.append([InlineKeyboardButton(text=f"🪙 {coin}", callback_data=f"analytics_coin_{coin}")])
                
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await message.answer("Выберите монету для детальной аналитики:", reply_markup=keyboard)

        @self.dp.callback_query(F.data.startswith("analytics_coin_"))
        async def process_analytics_coin_select(callback: CallbackQuery, state: FSMContext):
            await callback.answer()
            symbol = callback.data.replace("analytics_coin_", "")
            
            from ANALYTICS.plotter import generate_coin_analytics
            try:
                plot_path = generate_coin_analytics(symbol)
                if plot_path and os.path.exists(plot_path):
                    await callback.message.answer_photo(FSInputFile(plot_path), caption=f"📈 Analytics: {symbol}")
                else:
                    await callback.message.answer(f"❌ Не удалось сгенерировать аналитику для {symbol}.")
            except Exception as e:
                logger.error(f"Error generating coin analytics: {e}")
                await callback.message.answer(f"❌ Ошибка генерации аналитики для {symbol}: {e}")

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
                    
                    dump_path = os.path.join("logs", f"{symbol.lower()}_edit.json")
                    os.makedirs("logs", exist_ok=True)
                    with open(dump_path, "w", encoding="utf-8") as f:
                        f.write(rt_str)
                        
                    await message.answer("<b>Текущие настройки монеты:</b>\nОтредактируйте этот файл в любом редакторе и отправьте его обратно мне документом (либо скиньте текст).", reply_markup=self._get_cancel_keyboard(), parse_mode="HTML")
                    await message.answer_document(FSInputFile(dump_path))
                        
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
            if message.text and message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            json_str = ""
            if message.document:
                import io
                file = await self.bot.get_file(message.document.file_id)
                out = io.BytesIO()
                await self.bot.download_file(file.file_path, out)
                json_str = out.getvalue().decode('utf-8')
            elif message.text:
                json_str = message.text.strip()
            else:
                await message.answer("❌ Пожалуйста, отправьте текстовое сообщение или .json файл.")
                return
            
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
            
            dump_path = os.path.join("logs", "_base_edit.json")
            os.makedirs("logs", exist_ok=True)
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(base_str)
                
            await message.answer("<b>Текущий базовый шаблон _base.json:</b>\nОтредактируйте файл и отправьте обратно документом (или текстом).", reply_markup=self._get_cancel_keyboard(), parse_mode="HTML")
            await message.answer_document(FSInputFile(dump_path))
            await state.set_state(TGStates.waiting_for_base_json)

        @self.dp.message(TGStates.waiting_for_base_json)
        async def process_base_json(message: Message, state: FSMContext):
            if message.text and message.text == "🔙 Cancel":
                return await on_set_coins(message, state)
                
            json_str = ""
            if message.document:
                import io
                file = await self.bot.get_file(message.document.file_id)
                out = io.BytesIO()
                await self.bot.download_file(file.file_path, out)
                json_str = out.getvalue().decode('utf-8')
            elif message.text:
                json_str = message.text.strip()
            else:
                await message.answer("❌ Пожалуйста, отправьте текстовое сообщение или .json файл.")
                return
                
            import json
            try:
                new_base = json.loads(json_str)
                from c_utils import Utils
                Utils.write_json_file(self.template_manager.base_file, new_base)
                await message.answer("✅ Базовый шаблон успешно обновлен!", reply_markup=self._get_set_coins_keyboard())
                await state.clear()
            except Exception as e:
                await message.answer(f"❌ Ошибка JSON: {e}\nИсправьте и отправьте снова.")

        # =========================================================
        # EDIT ADVANCED
        # =========================================================
        @self.dp.message(F.text == "🔧 Advanced")
        async def on_advanced_btn(message: Message, state: FSMContext):
            from consts import DATA_DIR
            from c_utils import Utils
            import json
            app_json_path = DATA_DIR / "app.json"
            app_data = Utils.read_json_file(app_json_path)
            
            # Если нет секции advanced, создадим базовую
            if "advanced" not in app_data:
                app_data["advanced"] = {
                    "enabled": True,
                    "_comment_timeframe": "Valid values: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M",
                    "timeframe": "1d",
                    "window": 14,
                    "multiplier": 1.0,
                    "min_volatility_pct": 5.0,
                    "update_interval_hours": 12
                }
            
            adv_str = json.dumps(app_data["advanced"], indent=4)
            dump_path = os.path.join("logs", "advanced_edit.json")
            os.makedirs("logs", exist_ok=True)
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(adv_str)
                
            await message.answer("<b>Текущие настройки Advanced (Volatility):</b>\nОтредактируйте файл и отправьте обратно документом (или текстом).", reply_markup=self._get_cancel_keyboard(), parse_mode="HTML")
            await message.answer_document(FSInputFile(dump_path))
            await state.set_state(TGStates.waiting_for_advanced_json)

        @self.dp.message(TGStates.waiting_for_advanced_json)
        async def process_advanced_json(message: Message, state: FSMContext):
            if message.text and message.text == "🔙 Cancel":
                await state.clear()
                status = "⏸️ Paused" if self.bot_core.is_paused else "▶️ Running"
                await message.answer(f"<b>Control Panel</b>\nCurrent Status: {status}", reply_markup=self._get_main_keyboard(), parse_mode="HTML")
                return
                
            json_str = ""
            if message.document:
                import io
                file = await self.bot.get_file(message.document.file_id)
                out = io.BytesIO()
                await self.bot.download_file(file.file_path, out)
                json_str = out.getvalue().decode('utf-8')
            elif message.text:
                json_str = message.text.strip()
            else:
                await message.answer("❌ Пожалуйста, отправьте текстовое сообщение или .json файл.")
                return
                
            import json
            try:
                new_adv = json.loads(json_str)
                from c_utils import Utils
                from consts import DATA_DIR, _CFG
                app_json_path = DATA_DIR / "app.json"
                app_data = Utils.read_json_file(app_json_path)
                app_data["advanced"] = new_adv
                Utils.write_json_file(app_json_path, app_data)
                
                # Обновляем в памяти _CFG
                _CFG["advanced"] = new_adv
                
                # Заставляем пересчитаться
                if hasattr(self.bot_core, 'volatility_manager') and self.bot_core.volatility_manager.is_running:
                    asyncio.create_task(self.bot_core.volatility_manager.process_all())
                    
                await message.answer("✅ Настройки Advanced успешно обновлены! Перерасчет запущен.", reply_markup=self._get_main_keyboard())
                await state.clear()
            except Exception as e:
                await message.answer(f"❌ Ошибка JSON: {e}\nИсправьте и отправьте снова.")

    async def start(self):
        logger.info("Starting Telegram Receiver...")
        await self.dp.start_polling(self.bot)
