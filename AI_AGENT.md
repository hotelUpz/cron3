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


## 4. CRITICAL RULE:
- "NEVER run main.py, tests, or any mutating commands without EXPLICIT permission from the user." -- status: DESABLED


## 5. Recent Changes (28.06.2026)
- **Analytics Refactor**: TG menu modularized. Added Gross Profit & Net explicitly. Retained historical deleted coins in analytics menu with status flags.
- **Super Grid**: Renamed from Advanced. Toggling off via TG now instantly drops inactive grid prices and forces recalculation to standard indent in BotCore.
- **Validation**: Strict length parity checks added for grid and 	p_map on startup and TG JSON upload.

