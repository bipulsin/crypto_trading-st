import requests
import time
import hashlib
import hmac
import json
from config import API_KEY, API_SECRET, BASE_URL, SYMBOL_ID, SYMBOL, ASSET_ID
import threading
import concurrent.futures

class DeltaAPI:
    def __init__(self):
        # Use session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TradingBot/1.0',
            'Accept': 'application/json'
        })
        
        # Cache for frequently accessed data
        self._balance_cache = None
        self._balance_cache_time = 0
        self._balance_cache_duration = 30  # Cache for 30 seconds
        
        self._price_cache = None
        self._price_cache_time = 0
        self._price_cache_duration = 5  # Cache for 5 seconds
        
        # Thread lock for cache updates
        self._cache_lock = threading.Lock()

    def get_latest_price(self, symbol=SYMBOL):
        """Optimized price fetching with caching"""
        current_time = time.time()
        
        with self._cache_lock:
            if (self._price_cache is None or 
                current_time - self._price_cache_time > self._price_cache_duration):
                try:
                    url = f"{BASE_URL}/v2/tickers/{SYMBOL_ID}"
                    r = self.session.get(url, timeout=5)
                    r.raise_for_status()
                    data = r.json()
                    if data.get("success") and data.get("result"):
                        self._price_cache = float(data["result"]["mark_price"])
                        self._price_cache_time = current_time
                    else:
                        raise Exception("Failed to get latest price")
                except Exception as e:
                    print(f"   ⚠️  Could not fetch latest price: {e}")
                    return None
        
        return self._price_cache

    def get_candles(self, symbol=SYMBOL, interval='5m', limit=100, start=None, end=None):
        """
        Optimized candle fetching with connection pooling
        Handles empty result gracefully and prints a warning.
        """
        url = f"{BASE_URL}/v2/history/candles"
        params = {
            'symbol': symbol,
            'resolution': interval,
            'limit': limit
        }
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        try:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                if not data['result']:
                    print("Warning: No candle data returned from Delta Exchange API.")
                return data['result']
            else:
                raise Exception("Failed to get candles")
        except Exception as e:
            print(f"Error fetching candles: {e}")
            raise

    def get_candles_binance(self, symbol='BTCUSDT', interval='5m', limit=100):
        """
        Alternate method to fetch candles from Binance public API as a fallback.
        Returns a list of dicts with keys: time, open, high, low, close, volume
        """
        import requests
        url = f'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            klines = r.json()
            candles = []
            for k in klines:
                candles.append({
                    'time': int(k[0] // 1000),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            print(f"Fetched {len(candles)} candles from Binance")
            # print(candles)
            print("--------------------------------")
            return candles
        except Exception as e:
            print(f"Error fetching candles from Binance: {e}")
            return []

    def get_balance(self):
        """Optimized balance fetching with caching"""
        current_time = time.time()
        
        with self._cache_lock:
            if (self._balance_cache is None or 
                current_time - self._balance_cache_time > self._balance_cache_duration):
                try:
                    path = "/v2/wallet/balances"
                    headers, timestamp, message, signature = self.sign_request("GET", path)
                    r = self.session.get(BASE_URL + path, headers=headers, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    
                    wallet_balance = 0
                    for bal in data["result"]:
                        if str(bal.get("asset_id")) == str(ASSET_ID):
                            wallet_balance = float(bal['available_balance'])
                            break
                    
                    self._balance_cache = wallet_balance
                    self._balance_cache_time = current_time
                except Exception as e:
                    print(f"   ⚠️  Could not fetch wallet balance: {e}")
                    return 0
        
        return self._balance_cache

    def sign_request(self, method, path, body=None):
        """
        Sign request using HMAC SHA256 with proper message format
        """
        timestamp = str(int(time.time()))  # Use seconds, not milliseconds
        if body is None:
            body = ""
        else:
            body = json.dumps(body)  # Use default formatting with spaces
        message = method + timestamp + path + body  # Correct order for signature
        signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        headers = {
            "api-key": API_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json"
        }
        return headers, timestamp, message, signature

 

    def place_order(self, symbol, side, qty, order_type='limit_order', price=None, stop_loss=None, take_profit=None):
        """
        Place a limit order using the improved signing method
        Stop loss will be managed through position monitoring since Delta Exchange doesn't support
        direct stop loss orders in the way we need
        """
        start_time = time.time()
        if price is not None:
            print(f"🚀 Placing order: {side} {order_type} {qty} at ${price:.2f}")
            if stop_loss is not None:
                stop_loss = round(float(stop_loss), 2)
            else:
                stop_loss = price - 100
            if take_profit is not None:
                take_profit = round(float(take_profit), 2)
            else:
                take_profit = price + 100
        else:
            print(f"🚀 Placing order: {side} {order_type} {qty} at market")
 
        url = f"{BASE_URL}/v2/orders"
        path = "/v2/orders"
        qty = int(qty)
 
        data = {
            'product_id': SYMBOL_ID,
            'side': side,
            'order_type': 'limit_order',
            'size': qty,
            "limit_price": price,  # entry price for the bracket order
            "time_in_force": "gtc",
            "bracket_stop_loss_price": stop_loss,
            "bracket_stop_loss_limit_price": stop_loss,  # usually same as stop loss price for limit
            "bracket_take_profit_price": take_profit,
            "bracket_take_profit_limit_price": take_profit  # usually same as take profit price for limit
        }
        
        headers, timestamp, message, signature = self.sign_request('POST', path, data)
        
        # OPTIMIZATION: Reduced debug output for faster execution
        # print(f"DEBUG - URL: {url}")
        # print(f"DEBUG - Headers: {headers}")
        #print(f"DEBUG - Body: {json.dumps(data)}")
        # print(f"DEBUG - Timestamp: {timestamp}")
        # print(f"DEBUG - Signature: {signature}")
        
        try:
            r = self.session.post(url, headers=headers, json=data, timeout=15)
            r.raise_for_status()
            result = r.json()['result']
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error placing order: {e}")
            try:
                print(f"API response: {r.text}")
            except Exception:
                pass
            raise
        except Exception as e:
            print(f"❌ Error placing order: {e}")
            raise
        
        # Store stop loss information for manual monitoring
       
        
        execution_time = time.time() - start_time
        print(f"⚡ Order placed in {execution_time:.3f} seconds")
        
        return result


    def get_live_orders(self):
        """
        Get all live orders
        """
        path = "/v2/orders"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        r = self.session.get(BASE_URL + path, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            return data['result']
        else:
            raise Exception("Failed to get live orders")

    def cancel_order(self, order_id):
        """
        Cancel a specific order by ID
        """
        path = f"/v2/orders/{order_id}/cancel"
        headers, timestamp, message, signature = self.sign_request("POST", path)
        r = self.session.post(BASE_URL + path, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            return data['result']
        else:
            raise Exception(f"Failed to cancel order {order_id}")

    def cancel_all_orders(self):
        """
        Cancel all open orders - optimized for speed while maintaining safety
        """
        try:
            live_orders = self.get_live_orders()
            open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
            
            if not open_orders:
                print("   ℹ️  No open orders to cancel")
                return True
            
            print(f"   📋 Found {len(open_orders)} open orders to cancel")
            cancelled_count = 0
            
            # Use ThreadPoolExecutor for parallel cancellation
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_order = {
                    executor.submit(self.cancel_order, order['id']): order 
                    for order in open_orders
                }
                
                for future in concurrent.futures.as_completed(future_to_order):
                    order = future_to_order[future]
                    try:
                        result = future.result(timeout=5)
                        cancelled_count += 1
                        print(f"   ✅ Cancelled order {order['id']}")
                    except Exception as e:
                        print(f"   ❌ Failed to cancel order {order['id']}: {e}")
            
            if cancelled_count == len(open_orders):
                print(f"   ✅ Successfully cancelled all {cancelled_count} orders")
                return True
            else:
                print(f"   ⚠️  Cancelled {cancelled_count}/{len(open_orders)} orders")
                print(f"   ⚠️  {len(open_orders) - cancelled_count} orders require manual cancellation")
                return False
                
        except Exception as e:
            print(f"   ❌ Error getting live orders: {e}")
            return False

    def get_positions(self, product_id=84):
        """
        Get positions for a specific product
        """
        path = f"/v2/positions?product_id={product_id}"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        r = self.session.get(BASE_URL + path, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            return data['result']
        else:
            raise Exception("Failed to get positions")

    def close_all_positions(self, product_id=84):
        """
        Close all open positions for a specific product
        """
        try:
            # Get current positions
            positions = self.get_positions(product_id)
            if not positions:
                print("   ℹ️  No positions to close")
                return True
            
            # Handle single position object
            if isinstance(positions, dict):
                positions = [positions]
            
            # Filter positions with non-zero size
            open_positions = []
            for pos in positions:
                if isinstance(pos, dict) and float(pos.get('size', 0)) != 0:
                    open_positions.append(pos)
            
            if not open_positions:
                print("   ℹ️  No open positions to close")
                return True
            
            print(f"   📋 Found {len(open_positions)} position(s) to close")
            
            # Use ThreadPoolExecutor for parallel position closing
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_position = {}
                for pos in open_positions:
                    size = float(pos.get('size', 0))
                    if size > 0:
                        side = 'sell'
                        position_type = "LONG"
                    else:
                        side = 'buy'
                        position_type = "SHORT"
                    
                    close_size = abs(size)
                    print(f"   📊 Closing {position_type} position: {side.upper()} {close_size} lots")
                    
                    future = executor.submit(
                        self.place_order,
                        'BTCUSD', side, close_size, 'market_order', None, None
                    )
                    future_to_position[future] = pos
                
                success_count = 0
                for future in concurrent.futures.as_completed(future_to_position):
                    pos = future_to_position[future]
                    try:
                        result = future.result(timeout=10)
                        print(f"   ✅ Position close order placed: {result.get('id')}")
                        success_count += 1
                    except Exception as e:
                        print(f"   ❌ Failed to close position: {e}")
            
            if success_count == len(open_positions):
                print(f"   ✅ Successfully closed all {success_count} positions")
                return True
            else:
                print(f"   ⚠️  Closed {success_count}/{len(open_positions)} positions")
                return False
                
        except Exception as e:
            print(f"   ❌ Error closing positions: {e}")
            return False

    def close_position(self, product_id=84, size=None):
        """
        Close a specific position size (legacy method - use close_all_positions instead)
        """
        return self.close_all_positions(product_id)

    def get_account_state(self, product_id=84):
        """
        Optimized account state fetching with parallel operations
        """
        try:
            # Use ThreadPoolExecutor for parallel API calls
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                orders_future = executor.submit(self.get_live_orders)
                positions_future = executor.submit(self.get_positions, product_id)
                
                orders = orders_future.result(timeout=10)
                positions = positions_future.result(timeout=10)
            
            open_orders = [order for order in orders if order.get('state') in ['open', 'pending']]
            
            if positions:
                if isinstance(positions, dict):
                    positions = [positions]
                open_positions = [pos for pos in positions if isinstance(pos, dict) and float(pos.get('size', 0)) != 0]
            else:
                open_positions = []
            
            return {
                'orders': open_orders,
                'positions': open_positions,
                'has_orders': len(open_orders) > 0,
                'has_positions': len(open_positions) > 0,
                'is_clean': len(open_orders) == 0 and len(open_positions) == 0
            }
        except Exception as e:
            print(f"Error getting account state: {e}")
            return {
                'orders': [],
                'positions': [],
                'has_orders': False,
                'has_positions': False,
                'is_clean': False,
                'error': str(e)
            }

    def get_all_products(self):
        url = f"{BASE_URL}/v2/products"
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            return data['result']
        else:
            raise Exception("Failed to get products")

    def clear_cache(self):
        """Clear all caches"""
        with self._cache_lock:
            self._balance_cache = None
            self._balance_cache_time = 0
            self._price_cache = None
            self._price_cache_time = 0

    def __del__(self):
        """Cleanup session"""
        if hasattr(self, 'session'):
            self.session.close()
