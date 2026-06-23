import asyncio
from dotenv import load_dotenv
from consts import API_KEY, API_SECRET
from API.BINANCE.client import BinanceClient
import json

async def test():
    load_dotenv(override=True)
    client = BinanceClient(API_KEY, API_SECRET)
    
    res = await client.fetch_account_info()
    if res.success:
        data = res.data
        print(f"Total Unrealized: {data.get('totalUnrealizedProfit')}")
        positions = data.get('positions', [])
        for p in positions:
            if p.get('symbol') in ('WIFUSDT', 'STABLEUSDT'):
                print(p)
                
    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(test())
