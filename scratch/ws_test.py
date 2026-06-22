import asyncio
import aiohttp
import json
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consts import API_KEY

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("WSTest")

async def test_ws():
    logger.info("Creating session...")
    async with aiohttp.ClientSession() as session:
        # Get listenKey
        logger.info("Getting listenKey...")
        async with session.post(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": API_KEY},
        ) as r:
            data = await r.json()
            listen_key = data.get("listenKey")
            if not listen_key:
                logger.error(f"Failed to get listenKey: {data}")
                return

        logger.info(f"Got listenKey: {listen_key[:10]}...")

        # Activate keepalive once just to ensure it works
        await session.put(
            "https://fapi.binance.com/fapi/v1/listenKey",
            headers={"X-MBX-APIKEY": API_KEY},
        )

        ws_url = f"wss://fstream.binance.com/ws/{listen_key}"
        logger.info(f"Connecting to WS: {ws_url}")

        try:
            async with session.ws_connect(ws_url, autoping=True, timeout=15) as ws:
                logger.info("Connected! Waiting for messages. (Try to place an order manually or just wait)")
                while True:
                    msg = await asyncio.wait_for(ws.receive(), timeout=15.0)
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        logger.warning(f"Socket closed: {msg.type}")
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            json_data = json.loads(msg.data)
                            logger.info(f"Event Received: {json_data.get('e')} - Full payload: {json_data}")
                        except Exception as e:
                            logger.warning(f"Failed to parse msg: {e}")
        except asyncio.TimeoutError:
            logger.info("No messages in the last 15 seconds. Reconnecting loop in real bot would handle this, but for test we exit.")
        except Exception as e:
            logger.error(f"WS error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
