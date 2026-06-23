import asyncio
import os
import sys
import json
import aiohttp
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Добавляем пути
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import PositionStream
from POS_FSM.pos_stream_monitor import PositionMonitor
from POS_FSM.models import PositionState
from c_log import UnifiedLogger

logger = UnifiedLogger("WS_TESTER")
SYMBOL = "XRPUSDT"  # Используем дешевый символ для теста

print(f"DEBUG: API_KEY = '{API_KEY}'")
print(f"DEBUG: API_SECRET = '{API_SECRET}'")

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
        api_key=API_KEY,
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
        # Get current price to calculate QTY for 6 USDT
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={SYMBOL}") as resp:
                data = await resp.json()
                current_price = float(data["price"])
        
        target_usdt = 6.0
        qty = round(target_usdt / current_price)
        logger.info(f"Current price for {SYMBOL}: {current_price}, target USDT: {target_usdt}, calc QTY: {qty}")
        
        # 1. Лимитка, которая сразу исполнится
        logger.info("--- TESTING IMMEDIATE LIMIT ORDER ---")
        limit_price = round(current_price * 1.05, 4) # На 5% ВЫШЕ цены, исполнится как маркет
        res_limit = await client.make_order(SYMBOL, qty, "BUY", "LONG", "LIMIT", price=limit_price)
        logger.info(f"Limit Order placement result: {res_limit.success}")
        if not res_limit.success:
            logger.error("Failed to place limit order!")
        else:
            await asyncio.sleep(3)
            # Cancel limit order
            open_orders = await client.fetch_open_orders(SYMBOL)
            logger.info(f"Open orders: {open_orders}")
            await client.cancel_orders_for_side(SYMBOL, "LONG")
            logger.info("Limit order cancelled.")
            await asyncio.sleep(3)
        
        # 2. Открываем LONG (MARKET)
        logger.info("--- OPENING LONG ---")
        res = await client.make_order(SYMBOL, qty, "BUY", "LONG", "MARKET")
        logger.info(f"Open Order Result: {res.success}")
        if not res.success:
            logger.error("Failed to open position")
        
        # Ждем эвент
        await asyncio.sleep(3)
        state = fsm_states[SYMBOL]["LONG"]
        logger.info(f"State after OPEN: vol={state.total_volume}, price={state.avg_entry_price}")
        
        # 3. Закрываем
        logger.info("--- CLOSING LONG ---")
        # Ensure we sell only what we have
        res = await client.make_order(SYMBOL, qty, "SELL", "LONG", "MARKET")
        logger.info(f"Close Order Result: {res.success}")
        
        # Ждем эвент
        await asyncio.sleep(3)
        logger.info(f"State after CLOSE: vol={state.total_volume}, price={state.avg_entry_price}")
        
    except Exception as e:
        logger.exception("Test failed")
    finally:
        logger.info("Cleaning up...")
        try:
            await client.cancel_orders_for_side(SYMBOL, "LONG")
            await client.make_order(SYMBOL, qty, "SELL", "LONG", "MARKET")
        except:
            pass
        stop_flag = True
        stream.stop()
        await asyncio.sleep(1)
        await client.shutdown()

if __name__ == "__main__":
    asyncio.run(async_main())
