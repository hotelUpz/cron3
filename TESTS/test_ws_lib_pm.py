import asyncio
import websockets
import os
import json
from dotenv import load_dotenv
from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import BinanceListenKeyManager
import aiohttp
import sys

async def main():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    
    client = BinanceClient(api_key=api_key, api_secret=api_secret)
    session = aiohttp.ClientSession(trust_env=False)
    
    listen_mgr = BinanceListenKeyManager(api_key=api_key, session=session)
    listen_key = await listen_mgr.create()
    print(f"ListenKey: {listen_key[:5]}...")
    
    ws_url = f"wss://fstream.binance.com/pm/ws/{listen_key}"
    
    async def listen():
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                print(f"\nConnected to {ws_url}", flush=True)
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        print(f"\nReceived msg: {msg}", flush=True)
                    except TimeoutError:
                        print(".", end="", flush=True)
        except Exception as e:
            print(f"\nWS error: {e}", flush=True)
            
    task = asyncio.create_task(listen())
    
    await asyncio.sleep(2)
    print("\nPlacing test limit order...", flush=True)
    res = await client.make_order(symbol="TRXUSDT", qty=1000.0, side="BUY", position_side="LONG", market_type="LIMIT", price=0.01)
    print(f"Order created: {res.success}", flush=True)
    
    await asyncio.sleep(2)
    if res.success and "orderId" in res.data:
        print("Canceling order...", flush=True)
        await client.cancel_limit_orders("TRXUSDT", [res.data["orderId"]])
        
    await asyncio.sleep(3)
    task.cancel()
    await session.close()
    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
