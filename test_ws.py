import asyncio
import os
import sys

# Добавляем корень проекта в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consts import API_KEY, API_SECRET
from POS_FSM.pos_stream import PositionStream
from POS_FSM.pos_stream_monitor import PositionMonitor

async def main():
    monitor = PositionMonitor(states_cache={}, target_symbols=["WIFUSDT"])
    stream = PositionStream(
        api_key=API_KEY,
        stop_flag=lambda: False,
        monitor=monitor,
        target_symbols={"WIFUSDT"},
    )
    
    # Override handle messages to print all text
    original_handle = stream._handle_account_update
    async def debug_update(data):
        print("ACCOUNT_UPDATE:", data)
        await original_handle(data)
    stream._handle_account_update = debug_update

    print("Starting WS...")
    task = asyncio.create_task(stream.start())
    await asyncio.sleep(20)
    print("Test finished.")
    stream._external_stop = True
    await task

asyncio.run(main())
