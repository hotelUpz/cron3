import asyncio
import websockets

async def test_echo():
    url = "wss://echo.websocket.org"
    print(f"Connecting to {url}")
    try:
        async with websockets.connect(url) as ws:
            print("Connected!")
            await ws.send("Hello World!")
            print("Sent message.")
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"MSG 1: {msg}")
            msg2 = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"MSG 2: {msg2}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_echo())
