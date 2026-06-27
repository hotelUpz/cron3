import asyncio
import csv
from datetime import datetime, timezone
import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

def parse_time(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

async def main():
    client = BinanceClient(API_KEY, API_SECRET)
    
    input_file = "trades_ledger (43).csv"
    output_file = "trades_ledger_fixed.csv"
    
    rows = []
    with open(input_file, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        rows.append(header)
        for row in reader:
            if len(row) < 6: continue
            symbol, side, open_str, close_str, pnl, balance = row
            
            start_ts = parse_time(open_str)
            close_ts = parse_time(close_str)
            
            # For 0 open_time cases: 
            if "00:00:00" in open_str or "1970" in open_str: # just in case
                 start_ts = close_ts - (5 * 60 * 1000)
                 
            try:
                res = await client.get_income_pnl(symbol, side, start_ts, close_ts)
                if res:
                    new_pnl = round(res.get("net_pnl", 0.0), 4)
                    print(f"{symbol} {side} ({open_str} -> {close_str}): Old PnL {pnl}, New PnL {new_pnl}")
                    row[4] = str(new_pnl)
                else:
                    print(f"Failed to fetch for {symbol} {side}")
            except Exception as e:
                print(f"Error for {symbol} {side}: {e}")
                
            rows.append(row)
            await asyncio.sleep(0.5)
            
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(rows)
        
    print(f"Saved to {output_file}")

asyncio.run(main())
