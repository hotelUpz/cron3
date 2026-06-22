# ==============================================================================
# Path: main.py
# Role: Точка входа в приложение
# ==============================================================================

# main.py

from __future__ import annotations

import os
os.environ["PYDANTIC_DISABLE_MODEL_REBUILD"] = "1"

import asyncio
from typing import *


# ============================================================
# CORE APP (MAIN PROCESS ONLY)
# ============================================================
def main():
    import logging
    from c_log import UnifiedLogger
    from CORE.bot import BotCore
    
    logger = UnifiedLogger("App")
    
    try:
        bot = BotCore()
        logger.info("Starting BotCore...")
        asyncio.run(bot.start())
        
    except KeyboardInterrupt:
        logger.info("Ctrl+C detected. Shutting down...")
        try:
            asyncio.run(bot.shutdown())
        except Exception:
            pass
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        try:
            asyncio.run(bot.shutdown())
        except Exception:
            pass


if __name__ == "__main__":
    main()



## шпору не трогать!!
# # chmod 600 ssh_key.txt
# # eval "$(ssh-agent -s)" 
# # ssh-add ssh_key.txt
# # git remote set-url origin git@github.com:hotelUpz/uranus_bot.git
# # source .ssh-autostart.sh
# В терминале Git Bash, находясь в папке с проектом:
# source /c/Users/user/Desktop/My_Pro/HP_EliteBook_735/WORKSPACE/TRADING_SYSTEM/COMMON/.ssh-autostart.sh

# git push --set-upstream origin master
# # git config --global push.autoSetupRemote true
# # ssh -T git@github.com 
# # git log -1

# # git add .
# # git commit -m "plh37"
# # git push

# # pip install anthropic
# # npm install -g @anthropic-ai/claude-code

# # export ANTHROPIC_API_KEY=...
# taskkill /F /IM python.exe

# # claude