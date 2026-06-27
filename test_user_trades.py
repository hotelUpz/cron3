import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

async def main():
    client = BinanceClient(API_KEY, API_SECRET)
    res = await client._request("GET", "https://fapi.binance.com/fapi/v1/userTrades", params={"symbol": "STABLEUSDT", "limit": 5}, signed=True)
    if res.success:
        for t in res.data:
            print("side:", t.get("side"), "pos:", t.get("positionSide"), "realizedPnl:", t.get("realizedPnl"), "comm:", t.get("commission"), t.get("commissionAsset"))

asyncio.run(main())
