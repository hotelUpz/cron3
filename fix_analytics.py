import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

API_KEY = "7v6zi1UzPBTfQEK4W7JyI8tS1Rw1UiMzKls1AXt2yI8PGziGTOaTolzowaCG73SH"
API_SECRET = "WFPgh1XHQPQn0YU8V1HwtOWHbyKfGIqV67p6cK8ew3vi1GWTIzbWRRY4Ij7EsvWY"
BASE_URL = "https://fapi.binance.com"

def get_income_history():
    endpoint = "/fapi/v1/income"
    
    # 2026-06-27 23:29:50 UTC in ms
    start_time = 1782593390000 - (24 * 60 * 60 * 1000) # minus 24h just to be safe
    
    params = {
        "startTime": start_time,
        "limit": 1000,
        "timestamp": int(time.time() * 1000)
    }
    
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params["signature"] = signature
    
    headers = {
        "X-MBX-APIKEY": API_KEY
    }
    
    response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} {response.text}")
        return []

incomes = get_income_history()

total_realized = 0.0
total_funding = 0.0
total_commission = 0.0

print(f"Found {len(incomes)} income records.")
for item in incomes:
    inc_type = item.get("incomeType")
    val = float(item.get("income", 0.0))
    if inc_type == "REALIZED_PNL":
        total_realized += val
    elif inc_type == "FUNDING_FEE":
        total_funding += val
    elif inc_type == "COMMISSION":
        total_commission += val

print(f"Realized PnL: {total_realized:.4f}")
print(f"Funding: {total_funding:.4f}")
print(f"Commission: {total_commission:.4f}")
print(f"Net Profit (Sum): {total_realized + total_funding + total_commission:.4f}")
