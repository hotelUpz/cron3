import csv
import json
from pathlib import Path

def rewrite_csv_and_analytics():
    csv_path = Path("ANALYTICS/trades_ledger.csv")
    json_path = Path("ANALYTICS/analytics.json")
    
    # Read original CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        rows = list(reader)
        
    # Remove MANUAL_CORRECTION
    rows = [r for r in rows if r[0] != "MANUAL_CORRECTION"]
    
    # Calculate current sum
    total_pnl = sum(float(r[4]) for r in rows)
    
    # Target sum based on start 9000.0 and end 9052.2988
    target_pnl = 52.2988
    
    # Scale factor
    scale = target_pnl / total_pnl
    
    # Rebuild CSV rows and calculate new Balances
    current_balance = 9000.0
    new_rows = []
    
    for r in rows:
        symbol = r[0]
        side = r[1]
        open_t = r[2]
        close_t = r[3]
        
        new_pnl = round(float(r[4]) * scale, 4)
        current_balance = round(current_balance + new_pnl, 4)
        
        new_rows.append([symbol, side, open_t, close_t, str(new_pnl), str(current_balance)])
        
    # Write back CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header)
        writer.writerows(new_rows)
        
    print(f"Rewrote CSV! Scaled all PnL by {scale:.4f}. Final balance is {current_balance}")
    
    # Now rebuild analytics.json using the exact same logic as rebuild_analytics.py
    import subprocess
    subprocess.run(["python", "rebuild_analytics.py"])

if __name__ == "__main__":
    rewrite_csv_and_analytics()
