import asyncio
import os
import aiohttp
import websockets
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

async def test_stream():
    async with aiohttp.ClientSession() as session:
        async with session.post("https://fapi.binance.com/fapi/v1/listenKey", headers={"X-MBX-APIKEY": API_KEY}) as r:
            listen_key = (await r.json())["listenKey"]
            print(f"ListenKey: {listen_key}")
            
    url = f"wss://fstream-auth.binance.com/ws/{listen_key}"
    print(f"URL: {url}")
    
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from API.BINANCE.client import BinanceClient
    client = BinanceClient(API_KEY, API_SECRET)
    
    async with websockets.connect(url) as ws:
        print("WS connected (auth endpoint). Waiting 2s...")
        await asyncio.sleep(2)
        print("Making trade...")
        res = await client.make_order("XRPUSDT", 10, "BUY", "LONG", "MARKET")
        print(f"Order: {res.success}")
        
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                print(f"RAW MSG: {msg}")
            except asyncio.TimeoutError:
                print("Timeout!")
                break
                
        res = await client.make_order("XRPUSDT", 10, "SELL", "LONG", "MARKET")
        print(f"Close: {res.success}")
        await client.shutdown()

asyncio.run(test_stream())
