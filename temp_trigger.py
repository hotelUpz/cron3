import asyncio, json, os, time
from API.BINANCE.client import BinanceClient
from ANALYTICS.analytics import AnalyticsManager
from c_log import UnifiedLogger

async def trigger_sync():
    logger = UnifiedLogger("Trigger")
    with open('.env', 'r') as f:
        lines = f.readlines()
    ak = None
    sec = None
    for l in lines:
        if l.startswith('API_KEY ='):
            ak = l.split('=')[1].strip().strip('"')
        if l.startswith('API_SECRET ='):
            sec = l.split('=')[1].strip().strip('"')
            
    client = BinanceClient(ak, sec)
    am = AnalyticsManager()
    
    print("Triggering Deep Sync...")
    await am.deep_sync_analytics(client)
    print("Deep Sync complete.")
    await client._close_session()

if __name__ == "__main__":
    asyncio.run(trigger_sync())
