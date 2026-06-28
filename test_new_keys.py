import asyncio
from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

async def test_keys():
    client = BinanceClient(API_KEY, API_SECRET)
    
    # 1. Get current balance
    acc_res = await client.fetch_account_info()
    if not acc_res.success:
        print("Failed to fetch account:", acc_res.error_msg)
        return
        
    acc = acc_res.data
    margin_balance = float(acc.get("totalMarginBalance", 0.0))
    wallet_balance = float(acc.get("totalWalletBalance", 0.0))
    unrealized = float(acc.get("totalUnrealizedProfit", 0.0))
    print(f"Margin Balance: {margin_balance}")
    print(f"Wallet Balance: {wallet_balance}")
    print(f"Unrealized: {unrealized}")
    
    # 2. Get total income since start
    from datetime import datetime
    start_dt = datetime.strptime("2026-06-26 20:00:00", "%Y-%m-%d %H:%M:%S")
    start_ts = int(start_dt.timestamp() * 1000)
    
    end_ts = int(datetime.now().timestamp() * 1000)
    
    total_realized = 0.0
    total_commission = 0.0
    total_funding = 0.0
    
    # fetch all income (up to 1000 records per page)
    # just an approximation to see if it works
    import time
    res = await client._request("GET", "/fapi/v1/income", params={
        "startTime": start_ts,
        "endTime": end_ts,
        "limit": 1000
    })
    
    if res.success:
        records = res.data
        print(f"Found {len(records)} income records.")
        for r in records:
            itype = r.get("incomeType")
            val = float(r.get("income", 0.0))
            if itype == "REALIZED_PNL":
                total_realized += val
            elif itype == "COMMISSION":
                total_commission += val
            elif itype == "FUNDING_FEE":
                total_funding += val
                
        print(f"Realized: {total_realized}")
        print(f"Commission: {total_commission}")
        print(f"Funding: {total_funding}")
        print(f"Net Income: {total_realized + total_commission + total_funding}")
    else:
        print("Failed to fetch income:", res.error_msg)
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_keys())
