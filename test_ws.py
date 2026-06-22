import asyncio
import os
from dotenv import load_dotenv
from POS_FSM.pos_stream import PositionStream
from API.BINANCE.client import BinanceClient
from c_log import UnifiedLogger

logger = UnifiedLogger("TestWS")

class MockMonitor:
    def update_from_stream(self, symbol, side, pos_amt, entry_price):
        logger.info(f"MockMonitor update: {symbol} {side} amt={pos_amt} price={entry_price}")
        
    async def sync_from_rest(self, client, symbols):
        logger.info("MockMonitor sync_from_rest called")

async def main():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    
    if not api_key:
        logger.error("No API_KEY in .env")
        return
        
    client = BinanceClient(api_key=api_key, api_secret=api_secret)
        
    def stop_flag():
        return False
        
    monitor = MockMonitor()
    
    stream = PositionStream(
        api_key=api_key,
        stop_flag=stop_flag,
        monitor=monitor,
        target_symbols={"TRXUSDT"},
    )
    
    logger.info("Starting stream test...")
    task = asyncio.create_task(stream.start())
    
    await asyncio.sleep(4)
    
    logger.info("Placing a limit order to trigger ORDER_TRADE_UPDATE...")
    res = await client.make_order(
        symbol="TRXUSDT",
        qty=1000.0,
        side="BUY",
        position_side="LONG",
        market_type="LIMIT",
        price=0.05
    )
    logger.info(f"Place Limit Order: {res.success} {res.error_msg}")
    
    await asyncio.sleep(4)
    
    if res.success and res.data and isinstance(res.data, dict) and "orderId" in res.data:
        order_id = res.data["orderId"]
        logger.info(f"Canceling order {order_id}...")
        c_res = await client.cancel_limit_orders("TRXUSDT", [order_id])
        logger.info(f"Cancel Limit Order: {c_res.success} {c_res.error_msg}")
    
    await asyncio.sleep(4)
    
    logger.info("Stopping stream test...")
    stream.stop()
    await client.shutdown()
    
    try:
        await asyncio.wait_for(task, timeout=5.0)
    except Exception as e:
        logger.info(f"Task finished with {e}")

if __name__ == "__main__":
    asyncio.run(main())
