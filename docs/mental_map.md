# Ментальная карта проекта

## Архитектурные компоненты

1. **Config & Env (`CFG/`, `consts.py`)**
   - Константы, секреты, тайминги.
   - `runtime/`: Пер-символьные настройки (гриды, риски, таймфреймы, `tp_map`, `margin_type`, `leverage`).

2. **API (`API/BINANCE/`)**
   - `public.py`: Спецификации (`get_instruments`), публичные цены, стакан.
   - `client.py`: Приватный API (установка плечей, ордера, pnl).

3. **Core Logic (`CORE/`)**
   - `bot.py`: Главная торговая лупа `_game_loop`. Оркеструет всё.
   - `shedjuler.py`: `TimeControl` (таймеры, сигналы входа по интервалу).
   - `trade_math.py`: Математика (объем по risk-management, расчет цен TP).
   - `leverage_manager.py`: Кешируемый установщик `leverage` и `margin_type`.

4. **FSM & State (`FSM/`)**
   - `models.py`: `PositionState` (состояние позиции: `in_position`, `in_position_papper`, `pending_avg`, `avg_entry_price`).

## Торговый Pipeline

- `[Событие таймера]` -> `TimeControl.is_new_interval()` генерирует сигнал входа.
- `[Проверка стейта]` -> Если не `in_position` и не `in_position_papper`.
- `[Установка параметров]` -> `LeverageManager` ставит плечо и маржу (с кешированием).
- `[Расчет рисков]` -> `TradeMath` берет `invest_size` + `spec_data` и генерирует `volume`.
- `[Установка флага]` -> `state.in_position_papper = True` (для идемпотентности следующего такта `while` лупы).
- `[Размещение ордеров]` -> Входной ордер + расчет и постановка TP.
- `[В позиции]` -> Активация логики усреднения и `fallback_tp`.
