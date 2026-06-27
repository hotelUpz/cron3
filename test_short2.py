import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

def parse_time(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

async def main():
    client = BinanceClient(API_KEY, API_SECRET)
    start_ts = parse_time("2026-06-27 05:05:00")
    end_ts = parse_time("2026-06-27 16:01:12")
    trade_res = await client._request("GET", "https://fapi.binance.com/fapi/v1/userTrades", params={"symbol": "STABLEUSDT", "startTime": start_ts, "endTime": end_ts, "limit": 100}, signed=True)
    if trade_res.success:
        for t in trade_res.data:
            if t.get("positionSide") == "SHORT":
                print("SHORT trade:", datetime.fromtimestamp(t.get("time")/1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), t.get("side"), t.get("qty"), t.get("realizedPnl"), t.get("commission"))

asyncio.run(main())
