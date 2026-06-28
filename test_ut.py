import asyncio
import json
from API.BINANCE.client import BinanceClient

async def test():
    client = BinanceClient('7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx', 'MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW')
    res = await client._request('GET', 'https://fapi.binance.com/fapi/v1/userTrades', params={'symbol': 'STABLEUSDT', 'startTime': 1782494701000, 'limit': 1000}, signed=True)
    trades = [t for t in res.data if float(t.get('realizedPnl', 0)) != 0]
    print(json.dumps(trades[:3], indent=2))

asyncio.run(test())
