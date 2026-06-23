import asyncio
import os
import sys
import json
import aiohttp
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import BinanceListenKeyManager

async def listen_ws(listen_key):
    url = f"wss://fstream.binance.com/ws/{listen_key}"
    print(f"Connecting to {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            print("Connected. Waiting for messages...")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        print("\n=== MESSAGE RECEIVED ===")
                        data = json.loads(msg.data)
                        print(json.dumps(data, indent=2))
                        print("========================\n")
                    else:
                        print(f"Non-text message: {msg}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for messages...")
                except Exception as e:
                    print(f"WS error: {e}")
                    break

async def async_main():
    client = BinanceClient(API_KEY, API_SECRET)
    async with aiohttp.ClientSession() as session:
        listen_mgr = BinanceListenKeyManager(session=session, api_key=API_KEY)
        listen_key = await listen_mgr.create()
        print(f"Got listen_key: {listen_key[:10]}...")
        
        ws_task = asyncio.create_task(listen_ws(listen_key))
    
    print("Waiting 3 seconds for ws to connect...")
    await asyncio.sleep(3)
    
    # 1. Сначала тупо лимитки постановка и отмена
    print("--- TESTING LIMIT ORDER ---")
    res_limit = await client.make_order("XRPUSDT", 5, "BUY", "LONG", "LIMIT", price=1.0)
    print(f"Limit order: {res_limit.success}")
    await asyncio.sleep(2)
    
    print("Canceling orders...")
    await client.cancel_orders_for_side("XRPUSDT", "LONG")
    await asyncio.sleep(2)
    
    # 2. Открываем LONG (MARKET)
    print("--- OPENING LONG MARKET ---")
    res = await client.make_order("XRPUSDT", 5, "BUY", "LONG", "MARKET")
    print(f"Market Open: {res.success}")
    
    await asyncio.sleep(5)
    
    # 3. Закрываем LONG
    print("--- CLOSING LONG MARKET ---")
    res_close = await client.make_order("XRPUSDT", 5, "SELL", "LONG", "MARKET")
    print(f"Market Close: {res_close.success}")
    
    await asyncio.sleep(5)
    
    ws_task.cancel()
    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(async_main())
