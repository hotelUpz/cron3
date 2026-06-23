import asyncio
import os
import aiohttp
from dotenv import load_dotenv

async def get_listen_key_full_response():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    
    async with aiohttp.ClientSession(trust_env=False) as session:
        async with session.post(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": api_key},
        ) as r:
            text = await r.text()
            print("HTTP Status:", r.status)
            print("HTTP Headers:", dict(r.headers))
            print("HTTP Body:", text)

if __name__ == "__main__":
    asyncio.run(get_listen_key_full_response())
