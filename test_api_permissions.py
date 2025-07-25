#!/usr/bin/env python3
"""
Optimized test script to check API key permissions and performance on Delta Exchange testnet
"""
import requests
import time
import hmac
import hashlib
import json

BASE_URL = "https://cdn-ind.testnet.deltaex.org"
API_KEY = "Dif1lSZl16ibEVhqKboD1UkQ5Z4qD7"
API_SECRET = "kjDLM1vF5GI8THQylfIBRyMmfrL3pkheUomTBmJLCVJHwVCz0Fuk5KCA5WYH"
PROD_ID = 84
SYMBOL = "BTCUSD"
ASSET_ID = 3
MAX_TIME_DIFF = 5  # seconds

def sign_request(method, path, body=None):
    timestamp = str(int(time.time()))
    if body is None:
        body = ""
    else:
        body = json.dumps(body)
    message = method + timestamp + path + body
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    headers = {
        "api-key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }
    return headers, timestamp, message, signature

def print_time_diff(local_ts, server_time):
    try:
        local_ts = int(local_ts)
        server_time = int(server_time)
        diff = abs(server_time - local_ts) / 1000.0
        print(f"   [DEBUG] Local timestamp: {local_ts}, Server time: {server_time}, Diff: {diff:.3f} seconds")
        if diff > MAX_TIME_DIFF:
            print(f"   [WARNING] Clock difference is more than {MAX_TIME_DIFF} seconds! Please sync your system clock.")
    except Exception as e:
        print(f"   [DEBUG] Could not compute time diff: {e}")

def timed_request(func, *args, **kwargs):
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return None, elapsed, e

def get_wallet_balance():
    path = "/v2/wallet/balances"
    headers, timestamp, message, signature = sign_request("GET", path)
    r = requests.get(BASE_URL + path, headers=headers)
    r.raise_for_status()
    data = r.json()
    for bal in data.get("result", []):
        if str(bal.get("asset_id")) == str(ASSET_ID):
            return float(bal["available_balance"])
    return 0.0

def get_current_price():
    r = requests.get(f"{BASE_URL}/v2/tickers/{PROD_ID}")
    r.raise_for_status()
    ticker = r.json()
    if ticker.get("success") and ticker.get("result"):
        return float(ticker["result"]["mark_price"])
    return 0.0

def place_bracket_order(order_size, current_price):
    path = "/v2/orders"
    stop_order_body = {
        "product_id": PROD_ID,
        "size": order_size,
        "side": "buy",
        "order_type": "limit_order",
        "limit_price": current_price,
        "time_in_force": "gtc",
        "bracket_stop_loss_price": current_price - 200,
        "bracket_stop_loss_limit_price": current_price - 200,
        "bracket_take_profit_price": current_price + 300,
        "bracket_take_profit_limit_price": current_price + 300,
        "trail_amount": 20
    }
    headers, timestamp, message, signature = sign_request("POST", path, stop_order_body)
    r = requests.post(BASE_URL + path, headers=headers, json=stop_order_body)
    r.raise_for_status()
    return r.json()

def main():
    print("=== Testing API Key Permissions & Performance (REST API) ===\n")

    # 1. Public Endpoint
    print("1. Testing Public Endpoint:")
    _, elapsed, error = timed_request(requests.get, f"{BASE_URL}/v2/tickers/{PROD_ID}")
    if not error:
        print(f"   ✅ get_ticker: SUCCESS ({elapsed:.3f}s)")
    else:
        print(f"   ❌ get_ticker: FAILED - {error} ({elapsed:.3f}s)")

    # 2. Private Endpoint: Wallet Balance
    print("\n2. Testing Private Endpoint (Wallet Balance):")
    try:
        balance, elapsed, error = timed_request(get_wallet_balance)
        if not error:
            print(f"   ✅ get_balances: SUCCESS - USD balance: {balance} ({elapsed:.3f}s)")
        else:
            print(f"   ❌ get_balances: FAILED - {error} ({elapsed:.3f}s)")
    except Exception as e:
        print(f"   ❌ get_balances: FAILED - {e}")

    # 3. Trading Endpoint: Place Bracket Order
    print("\n3. Testing Trading Endpoint (Bracket Order):")
    try:
        wallet_balance = get_wallet_balance()
        current_price = get_current_price()
        leverage = 50
        if current_price > 0:
            order_size = int((0.5 * wallet_balance * leverage / current_price) * 1000)
        else:
            order_size = 10
        if order_size < 1:
            order_size = 1
        print(f"   Wallet balance: {wallet_balance}, Current price: {current_price}, Leverage: {leverage}")
        print(f"   Calculated order size: {order_size} lots")
        result, elapsed, error = timed_request(place_bracket_order, order_size, current_price)
        if not error:
            stop_order_id = result.get("result", {}).get("id", "N/A")
            print(f"   ✅ place_order (bracket): SUCCESS - Stop Order ID: {stop_order_id} ({elapsed:.3f}s)")
        else:
            print(f"   ❌ place_order: FAILED - {error} ({elapsed:.3f}s)")
            if hasattr(error, 'response') and error.response is not None:
                print(f"   Response: {error.response.text}")
    except Exception as e:
        print(f"   ❌ place_order: FAILED - {e}")

if __name__ == "__main__":
    main() 