import asyncio
import os
import sys
import json
from dotenv import load_dotenv
import aiohttp

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

WS_API_KEY = "bfj21Fj0de7mNUEyr0vKgs51OEY06UomexOOmWJWG0KUHUxzkrKkouBncDY8UdcB"

if not API_KEY or not API_SECRET:
    logger.error("API_KEY or API_SECRET not set in .env")

# Добавляем пути
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import PositionStream, BinanceListenKeyManager
from POS_FSM.pos_stream_monitor import PositionMonitor
from POS_FSM.models import PositionState
from c_log import UnifiedLogger

logger = UnifiedLogger("WS_TESTER")
SYMBOL = "XRPUSDT"  # Используем дешевый символ для теста

async def async_main():
    logger.info("Initializing WS Tester...")
    client = BinanceClient(API_KEY, API_SECRET)
    
    # 1. Setup Monitor
    fsm_states = {
        SYMBOL: {
            "LONG": PositionState(symbol=SYMBOL, side="LONG"),
            "SHORT": PositionState(symbol=SYMBOL, side="SHORT")
        }
    }
    monitor = PositionMonitor(states_cache=fsm_states, target_symbols=[SYMBOL])
    
    # 2. Setup Stream
    stop_flag = False
    stream = PositionStream(
        api_key=WS_API_KEY,
        stop_flag=lambda: stop_flag,
        monitor=monitor,
        target_symbols={SYMBOL},
        client=client
    )
    
    stream_task = asyncio.create_task(stream.start())
    
    # Ждем подключения
    for _ in range(20):
        if stream.ready:
            break
        await asyncio.sleep(0.5)
        
    if not stream.ready:
        logger.error("Failed to connect WS")
        stop_flag = True
        return
        
    logger.info("WS Connected. Starting trading tests...")
    
    try:
        qty = 10  # 10 XRP > 5 USDT
        logger.info(f"Target QTY for test: {qty}")
        
        # 2. Открываем LONG
        logger.info("--- OPENING LONG ---")
        res = await client.make_order(SYMBOL, qty, "BUY", "LONG", "MARKET")
        logger.info(f"Open Order Result: {res.success}")
        
        # Ждем эвент
        await asyncio.sleep(3)
        state = fsm_states[SYMBOL]["LONG"]
        logger.info(f"State after OPEN: vol={state.total_volume}, price={state.avg_entry_price}")
        
        # 3. Доливаемся
        logger.info("--- AVERAGING LONG ---")
        res = await client.make_order(SYMBOL, qty, "BUY", "LONG", "MARKET")
        logger.info(f"Avg Order Result: {res.success}")
        
        # Ждем эвент
        await asyncio.sleep(3)
        logger.info(f"State after AVG: vol={state.total_volume}, price={state.avg_entry_price}")
        
        # 4. Закрываем
        logger.info("--- CLOSING LONG ---")
        res = await client.make_order(SYMBOL, qty * 2, "SELL", "LONG", "MARKET")
        logger.info(f"Close Order Result: {res.success}")
        
        # Ждем эвент
        await asyncio.sleep(3)
        logger.info(f"State after CLOSE: vol={state.total_volume}, price={state.avg_entry_price}")
        
    except Exception as e:
        logger.exception("Test failed")
    finally:
        logger.info("Cleaning up...")
        if qty > 0:
            # Закрываем все позиции на всякий случай
            await client.make_order(SYMBOL, qty * 2, "SELL", "LONG", "MARKET")
        stop_flag = True
        stream.stop()
        await asyncio.sleep(1)
        await client.shutdown()

if __name__ == "__main__":
    asyncio.run(async_main())
