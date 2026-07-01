import json

def fix_analytics():
    with open('ANALYTICS/analytics.py', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Fix the realized_pnl assignment
    text = text.replace('data["realized_pnl_usdt"] = round(total_pnl, 4)', 'data["realized_pnl_usdt"] = round(total_pnl + total_comm + total_fund, 4)')

    # 2. Move _write_data
    old_block = """                    # Save before drawdown update
                    self._write_data(data)
                    
                # Update drawdowns logic calculates net_profit_usdt and cur_balance_usdt based on realized_pnl
                await self._update_drawdowns(client, data)
                logger.info(f"Absolute Deep Sync completed. PnL: {total_pnl}, Comm: {total_comm}")
"""
    new_block = """                # Update drawdowns logic calculates net_profit_usdt and cur_balance_usdt based on realized_pnl
                await self._update_drawdowns(client, data)
                
                # Save after drawdown update
                self._write_data(data)
                logger.info(f"Absolute Deep Sync completed. PnL: {total_pnl}, Comm: {total_comm}")
"""
    if old_block in text:
        text = text.replace(old_block, new_block)
        with open('ANALYTICS/analytics.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print("Fixed.")
    else:
        print("Block not found. Try running replacing manually.")

if __name__ == "__main__":
    fix_analytics()
