import asyncio
import websockets

async def test_public():
    url = "wss://fstream.binance.com/ws/xrpusdt@ticker"
    print(f"Connecting to {url}")
    async with websockets.connect(url) as ws:
        print("Connected!")
        for _ in range(3):
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"MSG: {msg}")

asyncio.run(test_public())
