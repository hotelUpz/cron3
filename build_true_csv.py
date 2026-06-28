import json
import csv
from datetime import datetime

def build_true_csv():
    with open("raw_income.json", "r") as f:
        data = json.load(f)
        
    pnl_events = [d for d in data if d["incomeType"] == "REALIZED_PNL"]
    
    symbols_to_track = ["STABLEUSDT", "SOLUSDT", "DASHUSDT", "JUPUSDT", "BNBUSDT", "XAGUSDT"]
    filtered_events = [d for d in pnl_events if d["symbol"] in symbols_to_track]
    
    # Sort chronologically
    filtered_events.sort(key=lambda x: x["time"])
    
    # Group by symbol and time (within 60 seconds)
    grouped_trades = []
    
    for event in filtered_events:
        sym = event["symbol"]
        ts = event["time"]
        income = float(event["income"])
        
        # Find if there is an open group for this symbol within 60s
        found_group = False
        if grouped_trades:
            last = grouped_trades[-1]
            if last["symbol"] == sym and (ts - last["end_time"]) <= 60000:
                last["end_time"] = ts
                last["pnl"] += income
                found_group = True
                
        if not found_group:
            grouped_trades.append({
                "symbol": sym,
                "start_time": ts,
                "end_time": ts,
                "pnl": income
            })
            
    print(f"Grouped into {len(grouped_trades)} trades.")
    
    # Build CSV
    current_balance = 9000.0
    rows = []
    
    for t in grouped_trades:
        sym = t["symbol"]
        pnl = round(t["pnl"], 4)
        current_balance = round(current_balance + pnl, 4)
        
        # Convert timestamp to string
        open_str = datetime.fromtimestamp(t["start_time"]/1000).strftime('%Y-%m-%d %H:%M:%S')
        close_str = datetime.fromtimestamp(t["end_time"]/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Side is unknown, assume SHORT (or figure out from userTrades)
        # We'll just put NONE since analytics only cares about PnL and Side is mostly for display
        rows.append([sym, "NONE", open_str, close_str, str(pnl), str(current_balance)])
        
    with open("true_ledger.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Symbol", "Side", "Open Time", "Close Time", "PnL (USDT)", "Balance"])
        writer.writerows(rows)
        
    print(f"Saved true_ledger.csv with {len(rows)} rows. Final Balance: {current_balance}")
    
    # Total PnL
    print(f"Total True PnL of these coins: {sum(t['pnl'] for t in grouped_trades)}")

if __name__ == "__main__":
    build_true_csv()
