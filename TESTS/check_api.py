import asyncio
import os
import sys
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from API.BINANCE.client import BinanceClient

async def async_main():
    client = BinanceClient(API_KEY, API_SECRET)
    
    print("Fetching /fapi/v2/account ...")
    res = await client._request("GET", "https://fapi.binance.com/fapi/v2/account", signed=True)
    if res.success:
        print("KEYS in account response:")
        print(res.data.keys())
        if "positions" in res.data:
            print("First position keys:")
            if len(res.data["positions"]) > 0:
                print(res.data["positions"][0])
            for p in res.data["positions"]:
                if p.get("symbol") == "XRPUSDT":
                    print("XRPUSDT position:")
                    print(p)
    else:
        print("Error fetch_positions:", res.error_msg)
        
    print("\nFetching /fapi/v2/positionRisk ...")
    res_risk = await client._request("GET", "https://fapi.binance.com/fapi/v2/positionRisk", signed=True)
    if res_risk.success:
        print("First position keys in risk:")
        if len(res_risk.data) > 0:
            print(res_risk.data[0])
            
    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(async_main())
