# ==============================================================================
# Path: consts.py
# Role: Глобальные константы и настройки конфигурации
# ==============================================================================

# const.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Где лежит const.json
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "CFG"
CFG_PATH = DATA_DIR / "app.json"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # намеренно без логгера, чтобы не было циклов импорта
        return {}

_CFG: Dict[str, Any] = _read_json(CFG_PATH)

# ============================================================
# SECRETS (.env only)
# ============================================================
API_KEY: str = os.getenv("API_KEY") or ""
API_SECRET: str = os.getenv("API_SECRET") or ""

# ============================================================
# APP / UTILS
# ============================================================
TIME_ZONE: str = str(_CFG["app"]["time_zone"])
PRECISION: int = int(_CFG["app"]["precision"])
SPEC_TTL_SEC: float = float(_CFG["app"]["spec_ttl_sec"])
TIME_SLACK_SEC: float = float(_CFG["app"]["time_slack_sec"])
REQ_TIMEOUT_SEC: float = float(_CFG["app"]["req_timeout_sec"])
AVOID_CHECK_RUNTIME_CFG: bool = bool(_CFG["app"].get("avoid_check_runtime_cfg", False))
API_RATE_LIMIT_SEC: float = float(_CFG["app"].get("api_rate_limit_sec", 0.1))
API_CONCURRENT_RATE_LIMIT_SEC: float = float(_CFG["app"].get("api_concurrent_rate_limit_sec", 0.01))
REST_FAILSAFE_SEC: float = float(_CFG["app"].get("rest_failsafe_sec", 5.0))
ANALYTICS_CSV_MAX_ROWS: int = int(_CFG.get("analytics", {}).get("csv_max_rows", 1000))

# ============================================================
# LOGGING
# ============================================================
LOG_DEBUG: bool = bool(_CFG["logging"]["debug"])
LOG_INFO: bool = bool(_CFG["logging"]["info"])
LOG_WARNING: bool = bool(_CFG["logging"]["warning"])
LOG_ERROR: bool = bool(_CFG["logging"]["error"])
MAX_LOG_LINES: int = int(_CFG["logging"]["max_log_lines"])
LOG_TO_CONSOLE: bool = bool(_CFG["logging"]["log_to_console"])
LOG_TO_FILE: bool = bool(_CFG["logging"]["log_to_file"])
