import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from API.BINANCE.client import BinanceClient
from POS_FSM.pos_stream import BinanceListenKeyManager

async def trigger_event(client):
    await asyncio.sleep(1)
    print("   [Trigger] Creating limit order...")
    res = await client.make_order(symbol="TRXUSDT", qty=1000.0, side="BUY", position_side="LONG", market_type="LIMIT", price=0.01)
    await asyncio.sleep(1)
    if res.success and "orderId" in res.data:
        print("   [Trigger] Canceling limit order...")
        await client.cancel_limit_orders("TRXUSDT", [res.data["orderId"]])

async def test_connection(name, headers, compress=0, proxy=None):
    load_dotenv()
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    client = BinanceClient(api_key=api_key, api_secret=api_secret)
    session = aiohttp.ClientSession(trust_env=True)
    listen_mgr = BinanceListenKeyManager(api_key=api_key, session=session)
    listen_key = await listen_mgr.create()
    
    ws_url = f"wss://fstream.binance.com/ws/{listen_key}"
    print(f"\n[{name}] Testing connection to {ws_url[:40]}...")
    
    try:
        ws = await session.ws_connect(
            ws_url,
            headers=headers,
            compress=compress,
            autoping=True,
            proxy=proxy,
            timeout=15.0
        )
        print(f"[{name}] Connected! Waiting for events...")
        
        trigger_task = asyncio.create_task(trigger_event(client))
        
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=4.0)
                print(f"[{name}] Received: {msg.type} {msg.data}")
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print("SUCCESS! Data received.")
                    break
            except asyncio.TimeoutError:
                print(f"[{name}] Timeout - NO DATA RECEIVED.")
                break
        await ws.close()
        await trigger_task
    except Exception as e:
        print(f"[{name}] Error: {e}")
        
    await session.close()
    await client.shutdown()

async def main():
    print("Testing different aiohttp WS headers and configurations to bypass DPI/Firewall...")
    await test_connection("Standard", {})
    
    headers_browser = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Origin": "https://www.binance.com",
    }
    await test_connection("Browser Mimic", headers_browser)
    
if __name__ == "__main__":
    asyncio.run(main())
