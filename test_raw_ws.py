import asyncio
import aiohttp
import os
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

async def test_stream():
    async with aiohttp.ClientSession() as session:
        # Get listenKey
        async with session.post(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": API_KEY}
        ) as resp:
            data = await resp.json()
            listen_key = data["listenKey"]
            print(f"Got listenKey: {listen_key}")
            
        url = f"wss://fstream.binance.com/ws/{listen_key}"
        print(f"Connecting to {url}")
        
        async with session.ws_connect(url) as ws:
            print("Connected! Waiting for events... (make a trade on your account!)")
            # We will wait for 20 seconds.
            while True:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=20.0)
                    print(f"RAW MSG: {msg}")
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        print(f"JSON: {json.loads(msg.data)}")
                except asyncio.TimeoutError:
                    print("Timeout... no message received in 20 seconds")
                    break

if __name__ == "__main__":
    asyncio.run(test_stream())
