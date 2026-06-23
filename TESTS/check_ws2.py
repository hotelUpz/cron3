import asyncio
import os
import sys
import json
import websockets
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import BinanceListenKeyManager
import aiohttp

async def listen_ws(listen_key):
    url = f"wss://fstream.binance.com/ws/{listen_key}"
    print(f"Connecting to {url} with websockets library...")
    try:
        async with websockets.connect(url) as ws:
            print("Connected! Waiting for messages...")
            while True:
                msg = await ws.recv()
                print("\n=== MESSAGE RECEIVED ===")
                try:
                    data = json.loads(msg)
                    print(json.dumps(data, indent=2))
                except:
                    print(msg)
                print("========================\n")
    except Exception as e:
        print(f"WS Error: {e}")

async def async_main():
    client = BinanceClient(API_KEY, API_SECRET)
    async with aiohttp.ClientSession() as session:
        listen_mgr = BinanceListenKeyManager(session=session, api_key=API_KEY)
        listen_key = await listen_mgr.create()
        print(f"Got listen_key: {listen_key[:10]}...")
        
        ws_task = asyncio.create_task(listen_ws(listen_key))
        
        print("Waiting 3 seconds...")
        await asyncio.sleep(3)
        
        print("--- OPENING MARKET ORDER ---")
        res = await client.make_order("XRPUSDT", 5, "BUY", "LONG", "MARKET")
        print(f"Market Open: {res.success}")
        
        await asyncio.sleep(5)
        
        print("--- CLOSING MARKET ORDER ---")
        res_close = await client.make_order("XRPUSDT", 5, "SELL", "LONG", "MARKET")
        print(f"Market Close: {res_close.success}")
        
        await asyncio.sleep(5)
        
        ws_task.cancel()
    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(async_main())
