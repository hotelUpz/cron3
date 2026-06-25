import csv
import json
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

ANALYTICS_DIR = Path(__file__).parent
CSV_FILE = ANALYTICS_DIR / "trades_ledger.csv"
JSON_FILE = ANALYTICS_DIR / "analytics.json"
PLOT_FILE = ANALYTICS_DIR / "equity_curve.png"

def generate_equity_curve() -> str:
    if not CSV_FILE.exists():
        return ""
        
    start_balance = 0.0
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                start_balance = float(data.get("start_balance_usdt", 0.0))
        except Exception:
            pass

    times = []
    balances = []
    
    current_balance = start_balance
    
    # We add the initial point
    try:
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return ""
                
            has_balance_col = "Balance" in header
            bal_idx = header.index("Balance") if has_balance_col else -1
            pnl_idx = header.index("PnL") if "PnL" in header else 4
            close_idx = header.index("Close Time") if "Close Time" in header else 3
            
            for row in reader:
                if len(row) <= close_idx:
                    continue
                
                # Parse time
                t_str = row[close_idx]
                try:
                    dt = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                    
                # Parse pnl / balance
                try:
                    if has_balance_col and len(row) > bal_idx and row[bal_idx].strip() != "":
                        current_balance = float(row[bal_idx])
                    else:
                        pnl = float(row[pnl_idx])
                        current_balance += pnl
                except ValueError:
                    continue
                    
                times.append(dt)
                balances.append(current_balance)
                
    except Exception as e:
        print(f"Error reading CSV for plot: {e}")
        return ""

    if not times:
        return ""

    # Prepend the start balance before the first trade (e.g. 1 hour before)
    from datetime import timedelta
    times.insert(0, times[0] - timedelta(hours=1))
    balances.insert(0, start_balance)
    
    plt.figure(figsize=(10, 5))
    plt.plot(times, balances, color="#2196F3", linewidth=2, label="Balance")
    
    # Fill under curve
    plt.fill_between(times, balances, min(balances), color="#2196F3", alpha=0.1)
    
    # Adjust Y axis dynamically based on data scale
    min_b = min(balances)
    max_b = max(balances)
    spread = max_b - min_b
    
    if spread < 5:
        pad = 1
    elif spread < 20:
        pad = 5
    else:
        pad = 10
        
    plt.ylim(min_b - pad, max_b + pad)
    
    plt.title("Equity Curve", fontsize=16, pad=15)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("USDT", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig(PLOT_FILE, dpi=100)
    plt.close()
    
    return str(PLOT_FILE)

if __name__ == "__main__":
    generate_equity_curve()
