import asyncio
import json
import csv
from datetime import datetime
from API.BINANCE.client import BinanceClient

API_KEY = "7jKhkRVyWE8RxAJbrA00vJdzb4dlnVqwzPdNW3RUlJvQ2Qzp4IsRyzhGcvVC3rOx"
API_SECRET = "MEY0emrK1HZrSfl7M9lZuOLF5MwSC7jhkUZ1AL1IMOXLK131f2ag8nZsZJHX9QIW"

async def build_true_ledger():
    client = BinanceClient(API_KEY, API_SECRET)
    symbols_to_track = ["STABLEUSDT", "SOLUSDT", "DASHUSDT", "JUPUSDT", "BNBUSDT", "XAGUSDT"]
    
    start_ts = 1782494701000 # 2026-06-26 20:25:01
    
    # get BNB price
    p_res = await client._request("GET", "https://fapi.binance.com/fapi/v1/ticker/price", params={"symbol": "BNBUSDT"})
    bnb_price = float(p_res.data.get("price", 580.0)) if p_res.success else 580.0
    
    all_trades = []
    
    for sym in symbols_to_track:
        current_start = start_ts
        while True:
            res = await client._request("GET", "https://fapi.binance.com/fapi/v1/userTrades", params={
                "symbol": sym,
                "startTime": current_start,
                "limit": 1000
            }, signed=True)
            
            if not res.success or not res.data:
                break
                
            trades = [t for t in res.data if float(t.get("realizedPnl", 0)) != 0]
            all_trades.extend(trades)
            
            if len(res.data) < 1000:
                break
            current_start = res.data[-1]["time"] + 1
            await asyncio.sleep(0.5)
            
    print(f"Found {len(all_trades)} position closing trades.")
    
    # Sort by time
    all_trades.sort(key=lambda x: x["time"])
    
    grouped_trades = []
    
    for t in all_trades:
        sym = t["symbol"]
        ts = t["time"]
        pnl = float(t["realizedPnl"])
        side = t["positionSide"] # LONG or SHORT
        
        c_val = float(t.get("commission", 0.0))
        c_asset = t.get("commissionAsset", "")
        if c_asset == "BNB":
            comm_usdt = c_val * bnb_price
        else:
            comm_usdt = c_val
            
        found = False
        if grouped_trades:
            last = grouped_trades[-1]
            if last["symbol"] == sym and last["side"] == side and (ts - last["end_time"]) <= 60000:
                last["end_time"] = ts
                last["gross_pnl"] += pnl
                last["commission"] += comm_usdt
                found = True
                
        if not found:
            grouped_trades.append({
                "symbol": sym,
                "side": side,
                "start_time": ts,
                "end_time": ts,
                "gross_pnl": pnl,
                "commission": comm_usdt
            })
            
    print(f"Grouped into {len(grouped_trades)} logical position closures.")
    
    current_balance = 9000.0
    rows = []
    
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
    
    for t in grouped_trades:
        sym = t["symbol"]
        net_pnl = t["gross_pnl"] - t["commission"] # commission is positive cost, subtract it
        
        current_balance += net_pnl
        
        open_str = datetime.fromtimestamp(t["start_time"]/1000).strftime('%Y-%m-%d %H:%M:%S')
        close_str = datetime.fromtimestamp(t["end_time"]/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        rows.append([sym, t["side"], open_str, close_str, f"{net_pnl:.4f}", f"{current_balance:.4f}"])
        
        data["total_trades"] += 1
        if net_pnl > 0:
            data["winning_trades"] += 1
            
        data["total_commission_usdt"] += t["commission"]
            
        if sym not in data["per_coin"]:
            data["per_coin"][sym] = {
                "total_trades": 0, "winning_trades": 0, "winrate_pct": 0.0,
                "gross_profit_usdt": 0.0, "net_profit_usdt": 0.0, "commission_usdt": 0.0,
                "funding_usdt": 0.0, "current_drawdown": 0.0, "max_net_profit": 0.0,
                "min_net_profit": 0.0, "max_drawdown": 0.0, "min_drawdown": 0.0,
                "avg_daily_profit": 0.0, "risk_reward_ratio": 0.0, "max_position_size": 0.0,
                "DRME": 0.0, "MDME": 0.0, "reward_risk_ratio": 0.0, "reward_risk_surplus_pct": 0.0
            }
            
        cdata = data["per_coin"][sym]
        cdata["total_trades"] += 1
        if net_pnl > 0:
            cdata["winning_trades"] += 1
            
        cdata["gross_profit_usdt"] = round(cdata["gross_profit_usdt"] + t["gross_pnl"], 4)
        cdata["commission_usdt"] = round(cdata["commission_usdt"] + t["commission"], 4)
        cdata["net_profit_usdt"] = round(cdata["gross_profit_usdt"] - cdata["commission_usdt"], 4)
        
        cdata["max_net_profit"] = round(max(cdata.get("max_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
        cdata["min_net_profit"] = round(min(cdata.get("min_net_profit", cdata["net_profit_usdt"]), cdata["net_profit_usdt"]), 4)
        
        if current_balance > peak:
            peak = current_balance
            trough = current_balance
        if current_balance < trough:
            trough = current_balance
        if current_balance < min_bal:
            min_bal = current_balance
            
        max_drawdown = trough - peak
        data["max_drawdown_usdt"] = round(min(data.get("max_drawdown_usdt", 0.0), max_drawdown), 4)

    # Fetch unrealized
    acc_res = await client.fetch_account_info()
    global_unrealized = 0.0
    if acc_res.success:
        positions = acc_res.data.get("positions", [])
        for p in positions:
            sym = p.get("symbol", "")
            if sym in data["per_coin"]:
                unrealized = float(p.get("unrealizedProfit", 0.0))
                data["per_coin"][sym]["current_drawdown"] = round(unrealized, 4)
                data["per_coin"][sym]["min_drawdown"] = round(min(0.0, unrealized), 4)
                data["per_coin"][sym]["net_profit_usdt"] = round(data["per_coin"][sym]["net_profit_usdt"] + unrealized, 4)
                global_unrealized += unrealized
                
    data["unrealized_pnl_usdt"] = round(global_unrealized, 4)

    for sym, cdata in data["per_coin"].items():
        if cdata["total_trades"] > 0:
            cdata["winrate_pct"] = round((cdata["winning_trades"] / cdata["total_trades"]) * 100, 2)
        data["gross_profit_usdt"] = round(data["gross_profit_usdt"] + cdata["gross_profit_usdt"], 4)
        
    data["net_profit_usdt"] = round(data["gross_profit_usdt"] - data["total_commission_usdt"] + global_unrealized, 4)
    data["cur_balance_usdt"] = round(9000.0 + data["net_profit_usdt"], 4)
    
    if data["total_trades"] > 0:
        data["winrate_pct"] = round((data["winning_trades"] / data["total_trades"]) * 100, 2)
        
    data["peak_balance_usdt"] = round(peak, 4)
    data["min_balance_usdt"] = round(min_bal, 4)
    data["_current_trough_usdt"] = round(trough, 4)
    data["performance_usdt"] = round(peak - 9000.0, 4)
    data["total_commission_usdt"] = round(data["total_commission_usdt"], 4)
    
    if data["max_drawdown_usdt"] < 0:
        data["recovery_factor"] = round(data["gross_profit_usdt"] / abs(data["max_drawdown_usdt"]), 2)
        
    with open("ANALYTICS/trades_ledger.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Symbol", "Side", "Open Time", "Close Time", "PnL (USDT)", "Balance"])
        writer.writerows(rows)
        
    with open("ANALYTICS/analytics.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print(f"Rebuilt true analytics! Gross: {data['gross_profit_usdt']}, Comm: {data['total_commission_usdt']}, Net: {data['net_profit_usdt']}, Bal: {data['cur_balance_usdt']}")
    await client._close_session()

if __name__ == "__main__":
    asyncio.run(build_true_ledger())
