# AI_AGENT.md — AI Quick Start

Читается первым. Содержит только навигацию и текущий контекст — всё остальное в первоисточниках ниже.

---

## 1. Первоисточники (читать в этом порядке)

| Документ | Что там |
|---|---|
| `../../../WORKSPACE/TRADING_SYSTEM/COMMON/DOCS/manifest.md` | Стандарты кодинга: SRP, лимиты строк (500 max, 150–350 gold), правила деплоя. |

| `../../../WORKSPACE/TRADING_SYSTEM/COMMON/DOCS/{PROJECT_NAME}/tech_debt.md` | Документ описывает основные технические долги и проблемы архитектуры, которые требуют немедленного устранения. |

| `../../../WORKSPACE/TRADING_SYSTEM/COMMON/DOCS/{PROJECT_NAME}/TZ.md` | **Все** бизнес-инварианты системы. Например: алгоритм балансировки, FSM инцидентов, газ-буфер, уведомления, ... |

| `../../../WORKSPACE/TRADING_SYSTEM/COMMON/wiki/{PROJECT_NAME}/` | Obsidian-заметки: архитектура, плейбук... |

---

## 2. Карта файлов (где что)

- ../../../WORKSPACE/TRADING_SYSTEM/COMMON/DOCS/
  - manifest.md
  - {PROJECT_NAME}/
- ../../../WORKSPACE/TRADING_SYSTEM/COMMON/wiki/
- {PROJECT_NAME}/

---

## 3. Режимы запуска

- `USE_TEST_KEYS=1` → `.env.test` + `CONFIG/test/` (те же реальные биржи, ключи разработчика)

---


## 4. Architectural Invariants (Methodology)

- **Analytics Integrity**: The bot is isolated from manual Binance withdrawals/deposits. `cur_balance_usdt` is strictly mathematically calculated as `start_balance_usdt + net_profit_usdt`. NEVER sync balance directly from Binance `/fapi/v2/account` to `cur_balance_usdt`.
- **Binance API Limits**: When fetching klines, `limit` MUST NOT exceed 1500 to prevent HTTP 400.
- **Volatility Calculations**: `VolatilityManager` calculates the *average* volatility per candle. If computing weekly volatility, `timeframe` must be `1w`, not `3m`.

---

## 5. CRITICAL RULE:
- "NEVER run main.py, tests, or any mutating commands without EXPLICIT permission from the user." -- status: DISABLED
