import csv
import json
import time
import datetime

def fix_all():
    # 1. Update analytics.json
    with open('ANALYTICS/analytics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # We found Start Balance was actually 85.3673 to make the math perfectly match Binance Wallet 85.9785
    data["start_balance_usdt"] = 85.3673
    
    # Binance actuals
    binance_realized = 1.1878
    binance_comm = -0.5770
    binance_fund = 0.0005
    
    # Bot's "gross_profit_usdt" is the sum of all PnL (which includes realized+comm+fund)
    actual_gross = round(binance_realized + binance_comm + binance_fund, 4) # 0.6113
    
    # We need to inject the difference into STABLEUSDT (or just global)
    # The current bot gross is 1.0904, we need it to be 0.6113. Difference = -0.4791
    correction_pnl = -0.4791
    
    # Update global stats
    data["gross_profit_usdt"] = actual_gross
    
    # Calculate new cur_balance
    unrealized = data.get("unrealized_pnl_usdt", 0.0)
    data["net_profit_usdt"] = round(actual_gross + unrealized, 4)
    data["cur_balance_usdt"] = round(data["start_balance_usdt"] + data["net_profit_usdt"], 4)
    
    with open('ANALYTICS/analytics.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    # 2. Append correction row to trades_ledger.csv
    # Calculate the Balance after correction
    # Wallet Balance after correction is 85.9785 (based on 85.3673 + 0.6112)
    # In ledger, Balance = Equity = Wallet + Unrealized
    ledger_balance = round(85.3673 + actual_gross + unrealized, 4)
    
    ts = int(time.time() * 1000)
    dt_str = datetime.datetime.fromtimestamp(ts / 1000.0, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    with open('ANALYTICS/trades_ledger.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["MANUAL_CORRECTION", "NONE", dt_str, dt_str, correction_pnl, ledger_balance])

    print("Correction applied! Added row to trades_ledger.csv and updated analytics.json.")

if __name__ == "__main__":
    fix_all()
