# ==============================================================================
# Path: run_scanner.py
# Role: Точка входа для запуска отдельного сканера волатильности
# ==============================================================================

import asyncio
from CORE.ADVANCED.volatility_scanner import run_scanner

if __name__ == "__main__":
    asyncio.run(run_scanner())
