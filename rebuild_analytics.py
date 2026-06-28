import csv
import json
from pathlib import Path

def rebuild():
    csv_path = Path("ANALYTICS/trades_ledger.csv")
    json_path = Path("ANALYTICS/analytics.json")
    
    if not csv_path.exists():
        print("No CSV found.")
        return
        
    start_balance = 9000.0
    
    data = {
        "start_balance_usdt": start_balance,
        "cur_balance_usdt": start_balance,
        "total_trades": 0,
        "winning_trades": 0,
        "winrate_pct": 0.0,
        "gross_profit_usdt": 0.0,
        "net_profit_usdt": 0.0,
        "unrealized_pnl_usdt": 0.0,
        "peak_balance_usdt": start_balance,
        "min_balance_usdt": start_balance,
        "_current_trough_usdt": start_balance,
        "max_drawdown_usdt": 0.0,
        "performance_usdt": 0.0,
        "recovery_factor": 0.0,
        "roi_pct": 0.0,
        "total_commission_usdt": 0.0,
        "total_funding_usdt": 0.0,
        "per_coin": {}
    }
    
    peak = start_balance
    trough = start_balance
    min_bal = start_balance
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        next(reader) # skip header
        
        for row in reader:
            if not row or len(row) < 6: continue
            if row[0] == "MANUAL_CORRECTION": continue
            
            symbol = row[0]
            pnl = float(row[4])
            balance = float(row[5])
            
            data["total_trades"] += 1
            if pnl > 0:
                data["winning_trades"] += 1
                
            if symbol not in data["per_coin"]:
                data["per_coin"][symbol] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "winrate_pct": 0.0,
                    "gross_profit_usdt": 0.0,
                    "net_profit_usdt": 0.0,
                    "commission_usdt": 0.0,
                    "funding_usdt": 0.0,
                    "current_drawdown": 0.0,
                    "max_net_profit": 0.0,
                    "min_net_profit": 0.0,
                    "max_drawdown": 0.0,
                    "min_drawdown": 0.0,
                    "avg_daily_profit": 0.0,
                    "risk_reward_ratio": 0.0,
                    "max_position_size": 0.0,
                    "DRME": 0.0,
                    "MDME": 0.0,
                    "reward_risk_ratio": 0.0,
                    "reward_risk_surplus_pct": 0.0
                }
                
            cdata = data["per_coin"][symbol]
            cdata["total_trades"] += 1
            if pnl > 0:
                cdata["winning_trades"] += 1
            cdata["gross_profit_usdt"] = round(cdata["gross_profit_usdt"] + pnl, 4)
            cdata["net_profit_usdt"] = cdata["gross_profit_usdt"]
            
            cdata["max_net_profit"] = round(max(cdata.get("max_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
            cdata["min_net_profit"] = round(min(cdata.get("min_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
            
            # Global Peak / Trough tracking
            if balance > peak:
                peak = balance
                trough = balance
            if balance < trough:
                trough = balance
            if balance < min_bal:
                min_bal = balance
                
            max_drawdown = trough - peak
            data["max_drawdown_usdt"] = round(min(data.get("max_drawdown_usdt", 0.0), max_drawdown), 4)

    # Calculate global totals
    for sym, cdata in data["per_coin"].items():
        if cdata["total_trades"] > 0:
            cdata["winrate_pct"] = round((cdata["winning_trades"] / cdata["total_trades"]) * 100, 2)
        data["gross_profit_usdt"] = round(data["gross_profit_usdt"] + cdata["gross_profit_usdt"], 4)
        
    data["net_profit_usdt"] = data["gross_profit_usdt"]
    
    # Auto-Correction to match the last known Binance balance!
    # The sum of PnL in the CSV often misses commissions or contains fake numbers (like 10.425).
    # We force the bot's mathematical Net Profit to match the Last Balance - Start Balance.
    true_net_profit = round(balance - start_balance, 4)
    correction = round(true_net_profit - data["net_profit_usdt"], 4)
    
    if correction != 0.0:
        print(f"Applying Auto-Correction of {correction} to align with final CSV balance {balance}")
        data["gross_profit_usdt"] = round(data["gross_profit_usdt"] + correction, 4)
        data["net_profit_usdt"] = data["gross_profit_usdt"]
        
        if "STABLEUSDT" in data["per_coin"]:
            data["per_coin"]["STABLEUSDT"]["gross_profit_usdt"] = round(data["per_coin"]["STABLEUSDT"]["gross_profit_usdt"] + correction, 4)
            data["per_coin"]["STABLEUSDT"]["net_profit_usdt"] = data["per_coin"]["STABLEUSDT"]["gross_profit_usdt"]

    data["cur_balance_usdt"] = round(start_balance + data["net_profit_usdt"], 4)
    if data["total_trades"] > 0:
        data["winrate_pct"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
        
    data["peak_balance_usdt"] = peak
    data["min_balance_usdt"] = min_bal
    data["_current_trough_usdt"] = trough
    data["performance_usdt"] = round(peak - start_balance, 4)
    
    if start_balance > 0:
        data["roi_pct"] = round(((data["cur_balance_usdt"] - start_balance) / start_balance) * 100, 2)
        
    if data["max_drawdown_usdt"] < 0:
        data["recovery_factor"] = round(data["gross_profit_usdt"] / abs(data["max_drawdown_usdt"]), 2)
        
    # Write to json
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print(f"Rebuilt analytics! Total Trades: {data['total_trades']}, Gross Profit: {data['gross_profit_usdt']}, Current Balance: {data['cur_balance_usdt']}")

if __name__ == "__main__":
    rebuild()
