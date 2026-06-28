import json

def fix_coin():
    with open('ANALYTICS/analytics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # We found the total difference between Bot's Gross Profit (sum of all trades)
    # and the actual Binance realized income is exactly -0.4791
    # We apply this directly to a coin so the auto-sum feature of the bot doesn't overwrite it.
    correction = -0.4791
    
    if "STABLEUSDT" in data["per_coin"]:
        cdata = data["per_coin"]["STABLEUSDT"]
        
        # apply correction
        cdata["gross_profit_usdt"] = round(cdata["gross_profit_usdt"] + correction, 4)
        cdata["net_profit_usdt"] = round(cdata["gross_profit_usdt"] + cdata.get("current_drawdown", 0.0), 4)
        
        # update global
        bot_gross = sum(v["gross_profit_usdt"] for v in data["per_coin"].values())
        data["gross_profit_usdt"] = round(bot_gross, 4)
        data["net_profit_usdt"] = round(bot_gross + data.get("unrealized_pnl_usdt", 0.0), 4)
        data["cur_balance_usdt"] = round(data["start_balance_usdt"] + data["net_profit_usdt"], 4)
        
        with open('ANALYTICS/analytics.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        print(f"Applied correction to STABLEUSDT! New Bot Gross Profit: {bot_gross}")
        print(f"New Current Balance: {data['cur_balance_usdt']}")
    else:
        print("STABLEUSDT not found.")

if __name__ == "__main__":
    fix_coin()
