import asyncio
import websockets
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)

async def main():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    
    # We will just use the listen_key from the previous script to avoid the REST call
    # Actually, we can make the REST call using aiohttp.
    import aiohttp
    async with aiohttp.ClientSession(trust_env=False) as session:
        async with session.post(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": api_key},
        ) as r:
            data = await r.json()
            listen_key = data["listenKey"]

    print("ListenKey:", listen_key)
    ws_url = f"wss://fstream.binance.com/ws/{listen_key}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected via websockets library! (DEBUG mode)")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    print(f"Received msg: {msg}")
                except asyncio.TimeoutError:
                    print("Timeout... no message.")
                    break
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
