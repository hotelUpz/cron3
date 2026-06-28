import asyncio
from datetime import datetime
from API.BINANCE.client import BinanceClient
import json

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

async def fetch_all_income():
    client = BinanceClient(API_KEY, API_SECRET)
    
    start_dt = datetime.strptime("2026-06-26 20:25:01", "%Y-%m-%d %H:%M:%S")
    start_ts = int(start_dt.timestamp() * 1000)
    
    all_income = []
    
    # We can fetch 1000 records at a time.
    limit = 1000
    current_start = start_ts
    
    while True:
        res = await client._request("GET", "https://fapi.binance.com/fapi/v1/income", params={
            "startTime": current_start,
            "limit": limit
        }, signed=True)
        
        if not res.success:
            print("Failed to fetch income:", res.error_msg)
            break
            
        records = res.data
        if not records:
            break
            
        all_income.extend(records)
        
        if len(records) < limit:
            break
            
        current_start = records[-1]["time"] + 1
        await asyncio.sleep(0.5)
        
    print(f"Fetched {len(all_income)} income records.")
    
    with open("raw_income.json", "w") as f:
        json.dump(all_income, f, indent=4)
        
if __name__ == "__main__":
    asyncio.run(fetch_all_income())
