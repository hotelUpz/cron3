import asyncio
import websockets
import json

async def test_ping():
    url = "wss://fstream.binance.com/ws/xrpusdt@ticker"
    print(f"Connecting to {url}")
    async with websockets.connect(url) as ws:
        print("Connected. Sending subscribe...")
        await ws.send(json.dumps({"method": "SUBSCRIBE", "params": ["btcusdt@ticker"], "id": 1}))
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"MSG: {msg}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test_ping())
