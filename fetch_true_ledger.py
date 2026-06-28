import asyncio
import csv
from datetime import datetime
from pathlib import Path
from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

async def rebuild_true_ledger():
    client = BinanceClient(API_KEY, API_SECRET)
    
    csv_path = Path("ANALYTICS/trades_ledger.csv")
    
    # 1. Read original CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        rows = list(reader)
        
    rows = [r for r in rows if r[0] != "MANUAL_CORRECTION"]
    
    # We will fetch the true PnL for each trade
    print("Fetching true PnL for each trade from Binance...")
    new_rows = []
    
    current_balance = 9000.0  # As user requested
    
    for r in rows:
        symbol = r[0]
        side = r[1]
        open_t_str = r[2]
        close_t_str = r[3]
        
        open_dt = datetime.strptime(open_t_str, "%Y-%m-%d %H:%M:%S")
        close_dt = datetime.strptime(close_t_str, "%Y-%m-%d %H:%M:%S")
        open_ts = int(open_dt.timestamp() * 1000)
        close_ts = int(close_dt.timestamp() * 1000)
        
        # Get true PnL
        res = await client.get_income_pnl(symbol, side, open_ts, close_ts)
        true_pnl = 0.0
        if res:
            true_pnl = res.get("net_pnl", 0.0)
            
        current_balance = round(current_balance + true_pnl, 4)
        
        print(f"[{symbol} {side}] {open_t_str} -> True PnL: {true_pnl:.4f} | Old PnL: {r[4]}")
        
        new_rows.append([symbol, side, open_t_str, close_t_str, f"{true_pnl:.4f}", f"{current_balance:.4f}"])
        
        await asyncio.sleep(0.5)  # Avoid rate limits
        
    # Write the true CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header)
        writer.writerows(new_rows)
        
    print(f"\nSaved true trades_ledger.csv! Final True Balance: {current_balance:.4f}")
    
    # 2. Fetch current unrealized PnL
    print("Fetching current unrealized PnL...")
    acc_res = await client.fetch_account_info()
    if not acc_res.success:
        print("Failed to fetch account for unrealized PnL:", acc_res.error_msg)
        return
        
    positions = acc_res.data.get("positions", [])
    coin_drawdowns = {}
    for p in positions:
        sym = p.get("symbol", "")
        unrealized = float(p.get("unrealizedProfit", 0.0))
        coin_drawdowns[sym] = coin_drawdowns.get(sym, 0.0) + unrealized
        
    # 3. Rebuild analytics.json
    print("Rebuilding analytics.json...")
    
    # run rebuild_analytics.py but WITHOUT the auto-correction because we have TRUE data now!
    import rebuild_analytics
    # we need to patch rebuild_analytics to include unrealized
    import json
    
    data = {
        "start_balance_usdt": 9000.0,
        "cur_balance_usdt": 9000.0,
        "total_trades": 0,
        "winning_trades": 0,
        "winrate_pct": 0.0,
        "gross_profit_usdt": 0.0,
        "net_profit_usdt": 0.0,
        "unrealized_pnl_usdt": 0.0,
        "peak_balance_usdt": 9000.0,
        "min_balance_usdt": 9000.0,
        "_current_trough_usdt": 9000.0,
        "max_drawdown_usdt": 0.0,
        "performance_usdt": 0.0,
        "recovery_factor": 0.0,
        "roi_pct": 0.0,
        "total_commission_usdt": 0.0,
        "total_funding_usdt": 0.0,
        "per_coin": {}
    }
    
    peak = 9000.0
    trough = 9000.0
    min_bal = 9000.0
    
    for r in new_rows:
        symbol = r[0]
        pnl = float(r[4])
        balance = float(r[5])
        
        data["total_trades"] += 1
        if pnl > 0:
            data["winning_trades"] += 1
            
        if symbol not in data["per_coin"]:
            data["per_coin"][symbol] = {
                "total_trades": 0, "winning_trades": 0, "winrate_pct": 0.0,
                "gross_profit_usdt": 0.0, "net_profit_usdt": 0.0, "commission_usdt": 0.0,
                "funding_usdt": 0.0, "current_drawdown": 0.0, "max_net_profit": 0.0,
                "min_net_profit": 0.0, "max_drawdown": 0.0, "min_drawdown": 0.0,
                "avg_daily_profit": 0.0, "risk_reward_ratio": 0.0, "max_position_size": 0.0,
                "DRME": 0.0, "MDME": 0.0, "reward_risk_ratio": 0.0, "reward_risk_surplus_pct": 0.0
            }
            
        cdata = data["per_coin"][symbol]
        cdata["total_trades"] += 1
        if pnl > 0:
            cdata["winning_trades"] += 1
        cdata["gross_profit_usdt"] = round(cdata["gross_profit_usdt"] + pnl, 4)
        cdata["net_profit_usdt"] = cdata["gross_profit_usdt"]
        
        cdata["max_net_profit"] = round(max(cdata.get("max_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
        cdata["min_net_profit"] = round(min(cdata.get("min_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
        
        if balance > peak:
            peak = balance
            trough = balance
        if balance < trough:
            trough = balance
        if balance < min_bal:
            min_bal = balance
            
        max_drawdown = trough - peak
        data["max_drawdown_usdt"] = round(min(data.get("max_drawdown_usdt", 0.0), max_drawdown), 4)

    # Insert Unrealized
    global_unrealized = 0.0
    for sym, unrealized in coin_drawdowns.items():
        if sym in data["per_coin"]:
            data["per_coin"][sym]["current_drawdown"] = round(unrealized, 4)
            data["per_coin"][sym]["min_drawdown"] = round(min(0.0, unrealized), 4)
            data["per_coin"][sym]["net_profit_usdt"] = round(data["per_coin"][sym]["gross_profit_usdt"] + unrealized, 4)
            global_unrealized += unrealized
            
    data["unrealized_pnl_usdt"] = round(global_unrealized, 4)

    for sym, cdata in data["per_coin"].items():
        if cdata["total_trades"] > 0:
            cdata["winrate_pct"] = round((cdata["winning_trades"] / cdata["total_trades"]) * 100, 2)
        data["gross_profit_usdt"] = round(data["gross_profit_usdt"] + cdata["gross_profit_usdt"], 4)
        
    data["net_profit_usdt"] = round(data["gross_profit_usdt"] + global_unrealized, 4)
    data["cur_balance_usdt"] = round(9000.0 + data["net_profit_usdt"], 4)
    if data["total_trades"] > 0:
        data["winrate_pct"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
        
    data["peak_balance_usdt"] = peak
    data["min_balance_usdt"] = min_bal
    data["_current_trough_usdt"] = trough
    data["performance_usdt"] = round(peak - 9000.0, 4)
    
    if data["max_drawdown_usdt"] < 0:
        data["recovery_factor"] = round(data["gross_profit_usdt"] / abs(data["max_drawdown_usdt"]), 2)
        
    with open("ANALYTICS/analytics.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print(f"Analytics successfully rebuilt directly from Binance! Current Equity: {data['cur_balance_usdt']:.4f}")

if __name__ == "__main__":
    asyncio.run(rebuild_true_ledger())
