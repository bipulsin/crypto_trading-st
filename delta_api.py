import requests
import time
import hashlib
import hmac
import json
from config import API_KEY, API_SECRET, BASE_URL, SYMBOL_ID, SYMBOL, ASSET_ID, LIVE_API_KEY, LIVE_API_SECRET, LIVE_BASE_URL, LIVE_SYMBOL_ID
import threading
import concurrent.futures

class DeltaAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TradingBot/1.0',
            'Accept': 'application/json'
        })
        self._balance_cache = None
        self._balance_cache_time = 0
        self._balance_cache_duration = 30
        self._price_cache = None
        self._price_cache_time = 0
        self._price_cache_duration = 5
        self._cache_lock = threading.Lock()

    def get_latest_price(self, symbol=SYMBOL):
        """Get latest price using LIVE parameters (market data)"""
        current_time = time.time()
        with self._cache_lock:
            if (self._price_cache is None or 
                current_time - self._price_cache_time > self._price_cache_duration):
                try:
                    url = f"{LIVE_BASE_URL}/v2/tickers/{LIVE_SYMBOL_ID}"
                    r = self.session.get(url, timeout=5)
                    r.raise_for_status()
                    data = r.json()
                    if data.get("success") and data.get("result"):
                        self._price_cache = float(data["result"]["mark_price"])
                        self._price_cache_time = current_time
                    else:
                        raise Exception("Failed to get latest price")
                except Exception as e:
                    return None
        return self._price_cache

    def get_candles(self, symbol=SYMBOL, interval='5m', limit=100, start=None, end=None):
        """Get candle data using LIVE parameters (market data)"""
        url = f"{LIVE_BASE_URL}/v2/history/candles"
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
            r = self.session.get(url, params=params, timeout=20)  # Increased timeout
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                return data['result']
            else:
                raise Exception("Failed to get candles")
        except Exception as e:
            raise

    def get_candles_binance(self, symbol='BTCUSDT', interval='5m', limit=100):
        """Get candle data from Binance (external API)"""
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
            return candles
        except Exception as e:
            return []

    def get_balance(self):
        """Get account balance using ORIGINAL parameters (trading operations)"""
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
                    return 0
        return self._balance_cache

    def sign_request(self, method, path, body=None):
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

    def sign_request_live(self, method, path, body=None):
        """Sign request using live API credentials for non-order related calls"""
        timestamp = str(int(time.time()))
        if body is None:
            body = ""
        else:
            body = json.dumps(body)
        message = method + timestamp + path + body
        signature = hmac.new(LIVE_API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        headers = {
            "api-key": LIVE_API_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json"
        }
        return headers, timestamp, message, signature

    def place_order(self, symbol, side, qty, order_type='limit_order', price=None, stop_loss=None, take_profit=None, post_only=False, max_retries=3):
        """Place order using ORIGINAL parameters (trading operations)"""
        if price is not None:
            if stop_loss is not None:
                stop_loss = round(float(stop_loss), 2)
            else:
                stop_loss = price - 100
            if take_profit is not None:
                take_profit = round(float(take_profit), 2)
            else:
                take_profit = price + 100
        url = f"{BASE_URL}/v2/orders"
        path = "/v2/orders"
        qty = int(qty)
        data = {
            'product_id': SYMBOL_ID,
            'side': side,
            'order_type': 'limit_order',
            'size': qty,
            "limit_price": price,
            "time_in_force": "gtc",
            "bracket_stop_loss_price": stop_loss,
            "bracket_stop_loss_limit_price": stop_loss,
            "bracket_take_profit_price": take_profit,
            "bracket_take_profit_limit_price": take_profit,
            "post_only": post_only
        }
        headers, timestamp, message, signature = self.sign_request('POST', path, data)
        
        for attempt in range(max_retries):
            try:
                # Increase timeout for order placement
                r = self.session.post(url, headers=headers, json=data, timeout=30)
                r.raise_for_status()
                response_data = r.json()
                
                # Check if the response is successful
                if not response_data.get('success'):
                    raise Exception(f"Order placement failed: {response_data.get('message', 'Unknown error')}")
                
                result = response_data['result']
                print(f"Order placement response: {result}")
                
                # Extract the correct order ID
                order_id = result.get('id')
                if order_id is None:
                    raise Exception("No order ID found in response")
                
                # Return a clean result with the correct order ID
                clean_result = {
                    'id': order_id,
                    'side': result.get('side'),
                    'size': result.get('size'),
                    'limit_price': result.get('limit_price'),
                    'state': result.get('state'),
                    'product_symbol': result.get('product_symbol'),
                    'bracket_stop_loss_price': result.get('bracket_stop_loss_price'),
                    'bracket_take_profit_price': result.get('bracket_take_profit_price'),
                    'created_at': result.get('created_at'),
                    'average_fill_price': result.get('average_fill_price')
                }
                
                return clean_result
                
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise Exception(f"Order placement timed out after {max_retries} attempts")
            except requests.exceptions.HTTPError as e:
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    raise

    def get_live_orders(self):
        """Get live orders using ORIGINAL parameters (trading operations)"""
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
        """Cancel a specific order using ORIGINAL parameters (trading operations)"""
        try:
            path = f"/v2/orders/{order_id}/cancel"
            headers, timestamp, message, signature = self.sign_request("POST", path)
            r = self.session.post(BASE_URL + path, headers=headers, timeout=10)
            
            # Handle 404 errors gracefully (order already cancelled or doesn't exist)
            if r.status_code == 404:
                return {"id": order_id, "status": "already_cancelled"}
            
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                return data['result']
            else:
                raise Exception("Failed to cancel order")
        except Exception as e:
            # Re-raise the exception with more context
            raise Exception(f"Failed to cancel order {order_id}: {e}")

    def cancel_all_orders(self):
        """Cancel all orders using the legacy method (individual cancellation)"""
        try:
            live_orders = self.get_live_orders()
            active_orders = [order for order in live_orders if order.get('state') not in ['filled', 'cancelled', 'rejected']]
            if not active_orders:
                return True
            
            cancelled_count = 0
            failed_count = 0
            
            for order in active_orders:
                try:
                    order_id = order['id']
                    result = self.cancel_order(order_id)
                    
                    if result and (isinstance(result, dict) and result.get('id')):
                        cancelled_count += 1
                    else:
                        failed_count += 1
                        
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_count += 1
            
            return cancelled_count > 0
        except Exception as e:
            return False

    def cancel_all_orders_by_product(self, product_id=None):
        """
        Cancel all open orders for a specific product ID using CancelAllFilterObject API
        
        Args:
            product_id (int): The product ID to cancel orders for. If None, uses SYMBOL_ID from config
            
        Returns:
            dict: Response with success status and details
        """
        if product_id is None:
            from config import SYMBOL_ID
            product_id = SYMBOL_ID
        
        try:
            payload = {"product_id": product_id}
            path = "/v2/orders/cancel_all"
            headers, timestamp, message, signature = self.sign_request("POST", path, payload)
            
            r = self.session.post(BASE_URL + path, headers=headers, json=payload, timeout=15)
            
            if r.status_code == 404:
                return {"success": True, "message": f"No orders found for product ID {product_id}"}
            
            r.raise_for_status()
            data = r.json()
            
            if data.get("success"):
                return {
                    "success": True,
                    "message": f"Successfully cancelled orders for product ID {product_id}",
                    "result": data.get('result', {})
                }
            else:
                return {
                    "success": False,
                    "message": f"API call failed: {data.get('message', 'Unknown error')}",
                    "result": data
                }
                
        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "message": f"HTTP Error: {e}",
                "result": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {e}",
                "result": None
            }

    def cancel_all_orders_with_filter(self, product_id=None, side=None, order_type=None):
        """
        Cancel all orders with advanced filtering using CancelAllFilterObject API
        
        Args:
            product_id (int): The product ID to cancel orders for
            side (str): Order side filter ('buy' or 'sell')
            order_type (str): Order type filter ('limit_order', 'market_order', etc.)
            
        Returns:
            dict: Response with success status and details
        """
        if product_id is None:
            from config import SYMBOL_ID
            product_id = SYMBOL_ID
        
        try:
            payload = {"product_id": product_id}
            
            if side:
                payload["side"] = side
            if order_type:
                payload["order_type"] = order_type
            
            path = "/v2/orders/cancel_all"
            headers, timestamp, message, signature = self.sign_request("POST", path, payload)
            
            r = self.session.post(BASE_URL + path, headers=headers, json=payload, timeout=15)
            
            r.raise_for_status()
            data = r.json()
            
            if data.get("success"):
                return {
                    "success": True,
                    "message": f"Successfully cancelled filtered orders for product ID {product_id}",
                    "result": data.get('result', {})
                }
            else:
                return {
                    "success": False,
                    "message": f"API call failed: {data.get('message', 'Unknown error')}",
                    "result": data
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {e}",
                "result": None
            }

    def get_positions(self, product_id=84):
        """Get positions using ORIGINAL parameters (trading operations)"""
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
        """Close all positions using ORIGINAL parameters (trading operations)"""
        try:
            positions = self.get_positions(product_id)
            if not positions:
                return True
            if isinstance(positions, dict):
                positions = [positions]
            open_positions = []
            for pos in positions:
                if isinstance(pos, dict) and float(pos.get('size', 0)) != 0:
                    open_positions.append(pos)
            if not open_positions:
                return True
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_position = {}
                for pos in open_positions:
                    size = float(pos.get('size', 0))
                    if size > 0:
                        side = 'sell'
                    else:
                        side = 'buy'
                    close_size = abs(size)
                    future = executor.submit(
                        self.place_order,
                        SYMBOL, side, close_size, 'market_order', None, None, None
                    )
                    future_to_position[future] = pos
                success_count = 0
                for future in concurrent.futures.as_completed(future_to_position):
                    pos = future_to_position[future]
                    try:
                        result = future.result(timeout=10)
                        success_count += 1
                    except Exception as e:
                        pass
            return success_count == len(open_positions)
        except Exception as e:
            return False

    def get_account_state(self, product_id=84):
        """Get account state using ORIGINAL parameters (trading operations)"""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                orders_future = executor.submit(self.get_live_orders)
                positions_future = executor.submit(self.get_positions, product_id)
                orders = orders_future.result(timeout=20)  # Increased timeout
                positions = positions_future.result(timeout=20)  # Increased timeout
            
            # Check for any orders that are not in 'filled' or 'cancelled' state
            active_orders = [order for order in orders if order.get('state') not in ['filled', 'cancelled', 'rejected']]
            
            if positions:
                if isinstance(positions, dict):
                    positions = [positions]
                open_positions = [pos for pos in positions if isinstance(pos, dict) and float(pos.get('size', 0)) != 0]
            else:
                open_positions = []
            
            return {
                'orders': active_orders,
                'positions': open_positions,
                'has_orders': len(active_orders) > 0,
                'has_positions': len(open_positions) > 0,
                'is_clean': len(active_orders) == 0 and len(open_positions) == 0
            }
        except Exception as e:
            return {
                'orders': [],
                'positions': [],
                'has_orders': False,
                'has_positions': False,
                'is_clean': False,
                'error': str(e)
            }

    def get_all_products(self):
        """Get all products using LIVE parameters (market data)"""
        url = f"{LIVE_BASE_URL}/v2/products"
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            return data['result']
        else:
            raise Exception("Failed to get products")

    def clear_cache(self):
        with self._cache_lock:
            self._balance_cache = None
            self._balance_cache_time = 0
            self._price_cache = None
            self._price_cache_time = 0

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()

    def edit_bracket_order(self, order_id, stop_loss=None, take_profit=None):
        """Edit bracket order using ORIGINAL parameters (trading operations)"""
        try:
            path = f"/v2/orders/{order_id}/edit_bracket"
            body = {}
            if stop_loss is not None:
                body['stop_loss_price'] = stop_loss
            if take_profit is not None:
                body['take_profit_price'] = take_profit
            
            headers, timestamp, message, signature = self.sign_request("POST", path, body)
            r = self.session.post(BASE_URL + path, headers=headers, json=body, timeout=10)
            
            # Handle 404 errors gracefully (order doesn't exist)
            if r.status_code == 404:
                raise Exception(f"Order {order_id} not found")
            
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                return data['result']
            else:
                raise Exception("Failed to edit bracket order")
        except Exception as e:
            # Re-raise the exception with more context
            raise Exception(f"Failed to edit bracket order {order_id}: {e}")
