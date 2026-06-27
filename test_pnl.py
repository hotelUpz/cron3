import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from API.BINANCE.client import BinanceClient
from consts import _CFG

async def main():
    client = BinanceClient(_CFG["api_key"], _CFG["api_secret"])
    res = await client._request("GET", "https://fapi.binance.com/fapi/v1/userTrades", params={"symbol": "STABLEUSDT", "limit": 10}, signed=True)
    if res.success:
        print("userTrades:", res.data[:2])
    
    res = await client._request("GET", "https://fapi.binance.com/fapi/v1/income", params={"symbol": "STABLEUSDT", "limit": 10, "incomeType": "FUNDING_FEE"}, signed=True)
    if res.success:
        print("income FUNDING_FEE:", res.data[:2])

asyncio.run(main())
