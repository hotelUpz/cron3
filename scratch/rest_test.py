import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from API.BINANCE.client import BinanceClient
from consts import API_KEY, API_SECRET

async def test_rest():
    client = BinanceClient(api_key=API_KEY, api_secret=API_SECRET)
    try:
        positions = await client.fetch_positions()
        for pos in positions:
            sym = pos.get("symbol")
            if sym == "STABLEUSDT":
                pos_side = pos.get("positionSide")
                pos_amt = pos.get("positionAmt")
                entry_price = pos.get("entryPrice")
                print(f"REST Pos: {sym} {pos_side} - Amt: {pos_amt}, Entry: {entry_price}")
    finally:
        pass

if __name__ == "__main__":
    asyncio.run(test_rest())
