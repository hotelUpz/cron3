import asyncio
import os
import sys
import json
import logging

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient

async def intercept_positions():
    client = BinanceClient(API_KEY, API_SECRET)
    print("=== INTERCEPTING REST POSITIONS ===")
    
    res = await client._request(
        "GET",
        "https://fapi.binance.com/fapi/v2/account",
        params={"recvWindow": 20000},
        signed=True
    )
    if res.success and "positions" in res.data:
        for p in res.data["positions"]:
            if p.get("symbol") == "XRPUSDT":
                print(f"RAW POSITION: {json.dumps(p)}")
    
    print("\n=== INTERCEPTING IMMEDIATE LIMIT ORDER ===")
    res_order = await client._request(
        "POST",
        "https://fapi.binance.com/fapi/v1/order",
        params={
            "symbol": "XRPUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": 5.0,
            "positionSide": "LONG",
            "recvWindow": 20000,
            "newOrderRespType": "RESULT",
            "price": 1.5,
            "timeInForce": "GTC"
        },
        signed=True
    )
    
    if res_order.success:
        print(f"RAW IMMEDIATE LIMIT ORDER: {json.dumps(res_order.data)}")
        
        # close position
        await client._request(
            "POST",
            "https://fapi.binance.com/fapi/v1/order",
            params={
                "symbol": "XRPUSDT",
                "side": "SELL",
                "type": "MARKET",
                "quantity": 5.0,
                "positionSide": "LONG",
                "recvWindow": 20000
            },
            signed=True
        )
    else:
        print(f"Failed to place test order: {res_order.error_msg}")

    print("\n=== INTERCEPTING EXCHANGE INFO ===")
    res_ex = await client._request("GET", "https://fapi.binance.com/fapi/v1/exchangeInfo")
    if res_ex.success and "symbols" in res_ex.data:
        for sym in res_ex.data["symbols"]:
            if sym["symbol"] == "XRPUSDT":
                print("RAW EXCHANGE INFO FILTERS:")
                print(json.dumps(sym["filters"], indent=2))
                break

    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(intercept_positions())
