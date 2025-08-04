import requests
import time
import hashlib
import hmac
import json
import pandas as pd
from config import API_KEY, API_SECRET, BASE_URL, SYMBOL_ID, SYMBOL, ASSET_ID, LIVE_API_KEY, LIVE_API_SECRET, LIVE_BASE_URL, LIVE_SYMBOL_ID
import threading
import concurrent.futures
from logger import get_logger

# Set up logger
logger = get_logger('delta_api', 'logs/delta_api.log')

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
                logger.info(f"Order placement response: {result}")
                
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
        """Edit bracket order stop loss and take profit"""
        try:
            url = f"{BASE_URL}/v2/orders/{order_id}"
            body = {}
            if stop_loss is not None:
                body['stop_loss'] = stop_loss
            if take_profit is not None:
                body['take_profit'] = take_profit
            
            if not body:
                return True  # Nothing to update
                
            headers = self.sign_request('PUT', f'/v2/orders/{order_id}', body)
            r = self.session.put(url, headers=headers, json=body, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data.get('success', False)
        except Exception as e:
            return False

    def get_order_status(self, order_id):
        """Get detailed status of a specific order"""
        try:
            url = f"{BASE_URL}/v2/orders/{order_id}"
            headers = self.sign_request('GET', f'/v2/orders/{order_id}')
            r = self.session.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            if data.get('success') and data.get('result'):
                return data['result']
            else:
                return None
        except Exception as e:
            return None

    def download_fills_history_csv(self, start_time=None, end_time=None, product_id=None):
        """
        Download fills history as CSV from Delta exchange
        
        Args:
            start_time (int, optional): Start time in milliseconds since epoch
            end_time (int, optional): End time in milliseconds since epoch  
            product_id (int, optional): Product ID to filter by. If None, uses SYMBOL_ID from config
            
        Returns:
            str: CSV content as string, or None if failed
        """
        if product_id is None:
            from config import SYMBOL_ID
            product_id = SYMBOL_ID
        
        try:
            path = "/v2/fills/history/download/csv"
            params = {"product_id": product_id}
            
            # If no time range specified, get last 30 days
            if start_time is None:
                import time
                end_time = int(time.time() * 1000)  # Current time in milliseconds
                start_time = end_time - (30 * 24 * 60 * 60 * 1000)  # 30 days ago
            
            if start_time is not None:
                params["start_time"] = start_time
            if end_time is not None:
                params["end_time"] = end_time
            
            # Build the query string for signing
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            path_with_params = f"{path}?{query_string}"
            
            headers, timestamp, message, signature = self.sign_request("GET", path_with_params)
            
            r = self.session.get(BASE_URL + path_with_params, headers=headers, timeout=30)
            r.raise_for_status()
            
            # Check if response is CSV
            content_type = r.headers.get('content-type', '')
            if 'text/csv' in content_type or 'application/octet-stream' in content_type:
                return r.text
            else:
                # Try to parse as JSON to get error message
                try:
                    data = r.json()
                    if not data.get('success'):
                        raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
                except:
                    pass
                raise Exception("Response is not CSV format")
                
        except Exception as e:
            logger.error(f"Error downloading fills history CSV: {e}")
            return None

    def get_ohlc_data(self, symbol=SYMBOL, resolution='5m', limit=100):
        """Fetch OHLC data from Delta Exchange (no authentication required)"""
        import time
        
        end_time = int(time.time())
        start_time = end_time - (limit * 5 * 60)  # 5 minutes per candle
        
        params = {
            'resolution': resolution,
            'symbol': symbol,
            'start': start_time,
            'end': end_time
        }
        
        url = f"{LIVE_BASE_URL}/v2/history/candles"
        
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                logger.error(f"Failed to fetch OHLC data: {data}")
                return pd.DataFrame()
            
            candle_data = data.get('result', [])
            if not candle_data:
                logger.warning("No OHLC data received")
                return pd.DataFrame()
            
            df = pd.DataFrame(candle_data)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Fetched {len(df)} OHLC candles")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLC data: {e}")
            return pd.DataFrame()

    def get_wallet_balance(self):
        """Get available wallet balance in USD"""
        try:
            response = self.make_request('GET', '/v2/wallet/balances')
            
            if not response.get('success', False):
                logger.error(f"Failed to fetch wallet balance: {response}")
                return 0.0
            
            balances = response.get('result', [])
            for balance in balances:
                if balance.get('asset_symbol') == 'USD':
                    available = float(balance.get('available_balance', 0))
                    logger.info(f"Available USD balance: {available}")
                    return available
            
            logger.warning("USD balance not found")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return 0.0

    def get_current_position(self, product_id=None):
        """Get current position for specified product"""
        import time
        
        if product_id is None:
            product_id = SYMBOL_ID
            
        # Add small delay to prevent rate limiting
        time.sleep(0.1)
        
        path = f"/v2/positions?product_id={product_id}"
        headers = self.sign_request("GET", path)
        
        try:
            url = f"{BASE_URL}{path}"
            logger.info(f"Fetching position from: {url}")
            response = self.session.get(url, headers=headers, timeout=10)
            
            logger.info(f"Position response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Position response text: {response.text}")
                return None
                
            data = response.json()
            
            if not data.get('success', False):
                logger.error(f"Failed to fetch position: {data}")
                return None
            
            position = data.get('result')
            
            # More thorough position checking
            if position:
                size = position.get('size', 0)
                if size != 0:
                    logger.info(f"Current position: Size={size}, Entry={position.get('entry_price')}, PnL={position.get('unrealized_pnl')}")
                    return position
                else:
                    logger.info("Position exists but size is 0 (closed position)")
                    return None
            else:
                logger.info("No position data returned from API")
                return None
                
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            return None

    def get_open_orders(self, product_id=None):
        """Get open orders for specified product"""
        if product_id is None:
            product_id = SYMBOL_ID
            
        path = f"/v2/orders?product_id={product_id}"
        headers = self.sign_request("GET", path)
        
        try:
            url = f"{BASE_URL}{path}"
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                logger.error(f"Failed to fetch open orders: {data}")
                return []
            
            orders = data.get('result', [])
            open_orders = [order for order in orders if order.get('state') in ['open', 'pending']]
            
            logger.info(f"Found {len(open_orders)} open orders")
            return open_orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    def place_market_order_with_trailing(self, side, size, stop_loss=None, take_profit=None, current_price=None, product_id=None, st_with_trailing=True):
        """Place market order with optional trailing stop loss"""
        if product_id is None:
            product_id = SYMBOL_ID
            
        order_data = {
            'product_id': product_id,
            'size': size,
            'side': side,
            'order_type': 'market_order'
        }
        
        # Add bracket orders with trailing stop loss if provided
        if stop_loss and take_profit and current_price:
            # Calculate trailing distance based on difference between current price and supertrend
            trailing_distance = abs(current_price - stop_loss)
            
            # Make trailing amount negative for buy orders, positive for sell orders
            if side == 'buy':
                bracket_trail_amount = -trailing_distance
            else:  # sell
                bracket_trail_amount = trailing_distance
            
            # Use trailing stop only if enabled
            if st_with_trailing:
                order_data.update({
                    # Bracket trailing stop loss parameters
                    "bracket_trail_amount": str(bracket_trail_amount),
                    "bracket_stop_trigger_method": "mark_price",
                    # Bracket take profit parameters  
                    "bracket_take_profit_price": str(take_profit),
                    "bracket_take_profit_limit_price": str(take_profit)  # Market order for TP
                })
                logger.info(f"Placing bracket order with trailing stop loss distance: {trailing_distance} (trail amount: {bracket_trail_amount})")
            else:
                # Use fixed stop loss without trailing
                order_data.update({
                    "bracket_stop_loss_price": str(stop_loss),
                    "bracket_stop_loss_limit_price": str(stop_loss),
                    "bracket_take_profit_price": str(take_profit),
                    "bracket_take_profit_limit_price": str(take_profit),
                    "bracket_stop_trigger_method": "mark_price"
                })
                logger.info(f"Placing bracket order with fixed stop loss: {stop_loss} (trailing disabled)")
        
        # Validate order data before sending
        if not self.validate_order_data(order_data):
            logger.error("Order data validation failed for market order")
            return None
        
        response = self.make_request('POST', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            order = response.get('result')
            logger.info(f"Order placed successfully: {side} {size} contracts at market price")
            if stop_loss:
                logger.info(f"Stop Loss: {stop_loss} (with trailing distance: {trailing_distance})")
            if take_profit:
                logger.info(f"Take Profit: {take_profit}")
            
            return order
        else:
            # Check for bracket order position exists error
            error_msg = str(response)
            if 'bracket_order_position_exists' in error_msg:
                logger.warning("Bracket order failed - position may exist. Trying simple market order...")
                
                # Try placing simple market order without bracket orders
                simple_order_data = {
                    'product_id': product_id,
                    'size': size,
                    'side': side,
                    'order_type': 'market_order'
                }
                
                simple_response = self.make_request('POST', '/v2/orders', data=simple_order_data)
                
                if simple_response.get('success', False):
                    order = simple_response.get('result')
                    logger.info(f"Simple market order placed successfully: {side} {size} contracts")
                    logger.warning("Bracket orders not available - position may already exist")
                    return order
                else:
                    logger.error(f"Failed to place simple market order: {simple_response}")
                    return None
            else:
                logger.error(f"Failed to place order: {response}")
                # Log the order data that failed
                logger.error(f"Failed order data: {order_data}")
                return None

    def validate_order_data(self, order_data):
        """Validate order data before sending"""
        required_fields = ['product_id', 'size', 'side', 'order_type']
        
        for field in required_fields:
            if field not in order_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate size
        size = order_data.get('size')
        if not isinstance(size, (int, float)) or size <= 0:
            logger.error(f"Invalid size: {size}")
            return False
        
        # Validate side
        side = order_data.get('side')
        if side not in ['buy', 'sell']:
            logger.error(f"Invalid side: {side}")
            return False
        
        # Validate order type
        order_type = order_data.get('order_type')
        if order_type not in ['market_order', 'limit_order']:
            logger.error(f"Invalid order type: {order_type}")
            return False
        
        return True

    def make_request(self, method, endpoint, params=None, data=None):
        """Make authenticated API request with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                timestamp = str(int(time.time()))
                path = endpoint
                
                if params:
                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    path += f"?{query_string}"
                
                # sign_request returns (headers, timestamp, message, signature)
                headers, _, _, _ = self.sign_request(method, path, data)
                url = f"{BASE_URL}{path}"
                
                if method.upper() == 'GET':
                    response = self.session.get(url, headers=headers, timeout=10)
                elif method.upper() == 'POST':
                    response = self.session.post(url, headers=headers, json=data, timeout=10)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, headers=headers, json=data, timeout=10)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, headers=headers, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} request attempts failed")
                    return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}

    def process_trades_from_fills_history(self, product_id=None, save_csv=True):
        """
        Download fills history CSV from Delta exchange and process it into trades
        
        Args:
            product_id (int, optional): Product ID to filter by. If None, uses SYMBOL_ID from config
            save_csv (bool): Whether to save the processed trades to CSV file
            
        Returns:
            pd.DataFrame: Processed trades dataframe
        """
        if product_id is None:
            from config import SYMBOL_ID
            product_id = SYMBOL_ID
        
        try:
            # Try different time ranges to get fills data
            import time
            current_time = int(time.time() * 1000)
            
            # Try different time periods: 7 days, 30 days, 90 days
            time_periods = [
                (current_time - (7 * 24 * 60 * 60 * 1000), current_time, "7 days"),
                (current_time - (30 * 24 * 60 * 60 * 1000), current_time, "30 days"),
                (current_time - (90 * 24 * 60 * 60 * 1000), current_time, "90 days")
            ]
            
            csv_content = None
            period_used = None
            
            for start_time, end_time, period_name in time_periods:
                logger.info(f"Trying to download fills for {period_name}...")
                csv_content = self.download_fills_history_csv(
                    start_time=start_time, 
                    end_time=end_time, 
                    product_id=product_id
                )
                
                if csv_content and len(csv_content.strip()) > 200:  # More than just headers
                    period_used = period_name
                    logger.info(f"Successfully downloaded fills for {period_name}")
                    break
                else:
                    logger.warning(f"No fills data found for {period_name}")
            
            if not csv_content or len(csv_content.strip()) <= 200:
                logger.error("No fills data found for any time period")
                return pd.DataFrame()
            
            # Parse CSV content
            import io
            df = pd.read_csv(io.StringIO(csv_content))
            
            if df.empty:
                logger.warning("No fills data found after parsing")
                return df
            
            logger.info(f"Downloaded {len(df)} fills records for {period_used}")
            
            # Process the fills into trades
            trades_df = self._process_fills_to_trades(df)
            
            if save_csv and not trades_df.empty:
                # Save processed trades to CSV
                timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                filename = f'trades_report.csv'
                trades_df.to_csv(filename, index=False)
                logger.info(f"Trades report saved to: {filename}")
            
            return trades_df
            
        except Exception as e:
            logger.error(f"Error processing trades from fills history: {e}")
            return pd.DataFrame()

    def _process_fills_to_trades(self, df):
        """
        Process fills dataframe into trades dataframe
        
        Args:
            df (pd.DataFrame): Raw fills dataframe
            
        Returns:
            pd.DataFrame: Processed trades dataframe
        """
        try:
            # Ensure required columns exist
            required_columns = ['Time', 'Side', 'Filled Qty', 'Value', 'Fees paid']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                logger.info(f"Available columns: {list(df.columns)}")
                return pd.DataFrame()
            
            # Parse datetime
            df['Time'] = pd.to_datetime(df['Time'].str.split('+').str[0], errors='coerce')
            
            # Sort by time
            df = df.sort_values('Time').reset_index(drop=True)
            
            # Filter out rows with NaT in Time column
            df = df.dropna(subset=['Time'])
            
            if df.empty:
                logger.warning("No valid fills data after filtering")
                return df
            
            logger.info(f"Processing {len(df)} fills records")
            logger.info(f"Buy fills: {len(df[df['Side'] == 'buy'])}")
            logger.info(f"Sell fills: {len(df[df['Side'] == 'sell'])}")
            
            # Improved trade pairing logic
            trades = []
            processed_indices = set()
            
            # Group fills by order ID first to understand the structure
            order_groups = df.groupby('Order ID')
            logger.info(f"Found {len(order_groups)} unique order IDs")
            
            # Create a mapping of order IDs to their fills
            order_fills = {}
            for order_id, group in order_groups:
                order_fills[order_id] = group.sort_values('Time').reset_index(drop=True)
            
            # Sort all fills by time for sequential processing
            all_fills = df.sort_values('Time').reset_index(drop=True)
            
            # Process fills sequentially to find trade pairs
            for i, fill in all_fills.iterrows():
                if i in processed_indices:
                    continue
                
                current_side = fill['Side']
                current_order_id = fill.get('Order ID', '')
                current_time = fill['Time']
                
                # Look for the next opposite side fill within a reasonable time window
                opposite_side = 'sell' if current_side == 'buy' else 'buy'
                
                # Find all opposite side fills that come after this fill
                future_opposite_fills = all_fills[
                    (all_fills.index > i) & 
                    (all_fills['Side'] == opposite_side) & 
                    (~all_fills.index.isin(processed_indices))
                ]
                
                if not future_opposite_fills.empty:
                    # Find the closest opposite fill in time (within 24 hours)
                    time_diff = (future_opposite_fills['Time'] - current_time).abs()
                    valid_matches = future_opposite_fills[time_diff <= pd.Timedelta(hours=24)]
                    
                    if not valid_matches.empty:
                        # Take the closest match
                        closest_idx = time_diff.idxmin()
                        opposite_fill = all_fills.loc[closest_idx]
                        
                        # Calculate trade metrics
                        entry_qty = float(fill['Filled Qty'])
                        exit_qty = float(opposite_fill['Filled Qty'])
                        
                        # Use the smaller quantity to ensure complete trade
                        trade_qty = min(entry_qty, exit_qty)
                        
                        # Determine which is entry and which is exit
                        if current_side == 'buy':
                            entry_fill = fill
                            exit_fill = opposite_fill
                            trade_side = 'Long'
                        else:
                            entry_fill = opposite_fill
                            exit_fill = fill
                            trade_side = 'Short'
                        
                        # Calculate proportional values
                        entry_cashflow = float(entry_fill['Value']) * (trade_qty / float(entry_fill['Filled Qty']))
                        exit_cashflow = float(exit_fill['Value']) * (trade_qty / float(exit_fill['Filled Qty']))
                        
                        entry_fees = float(entry_fill['Fees paid']) * (trade_qty / float(entry_fill['Filled Qty']))
                        exit_fees = float(exit_fill['Fees paid']) * (trade_qty / float(exit_fill['Filled Qty']))
                        
                        # Calculate net cashflow and fees
                        if trade_side == 'Long':
                            net_cashflow = exit_cashflow - entry_cashflow
                        else:
                            net_cashflow = entry_cashflow - exit_cashflow
                        
                        total_fees = entry_fees + exit_fees
                        
                        # Calculate P&L
                        pnl = net_cashflow - total_fees
                        
                        trade = {
                            'Entry Time': entry_fill['Time'],
                            'Exit Time': exit_fill['Time'],
                            'Entry ID': entry_fill.get('Order ID', ''),
                            'Exit ID': exit_fill.get('Order ID', ''),
                            'Side': trade_side,
                            'Quantity': trade_qty,
                            'Entry Price': entry_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Exit Price': exit_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Cashflow': net_cashflow,
                            'Trading Fees': total_fees,
                            'Realised P&L': pnl,
                            'Duration': (exit_fill['Time'] - entry_fill['Time']).total_seconds() / 3600  # hours
                        }
                        
                        trades.append(trade)
                        
                        # Mark both fills as processed
                        processed_indices.add(i)
                        processed_indices.add(closest_idx)
                        
                        logger.debug(f"Matched trade: {trade_side} {trade_qty} contracts, Entry: {entry_fill.get('Order ID')}, Exit: {exit_fill.get('Order ID')}, P&L: ${pnl:.2f}")
            
            if not trades:
                logger.warning("No complete trades found")
                return pd.DataFrame()
            
            trades_df = pd.DataFrame(trades)
            
            # Calculate statistics
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['Realised P&L'] > 0])
            losing_trades = len(trades_df[trades_df['Realised P&L'] < 0])
            total_pnl = trades_df['Realised P&L'].sum()
            total_fees = trades_df['Trading Fees'].sum()
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            logger.info(f"Processed {total_trades} trades:")
            logger.info(f"  Winning trades: {winning_trades} ({win_rate:.1f}%)")
            logger.info(f"  Losing trades: {losing_trades}")
            logger.info(f"  Total P&L: ${total_pnl:.2f}")
            logger.info(f"  Total fees: ${total_fees:.2f}")
            
            # Log some sample trades for verification
            if not trades_df.empty:
                logger.info("Sample trades:")
                for i, trade in trades_df.head(3).iterrows():
                    logger.info(f"  {trade['Side']}: Entry {trade['Entry ID']} -> Exit {trade['Exit ID']}, P&L: ${trade['Realised P&L']:.2f}")
            
            return trades_df
            
        except Exception as e:
            logger.error(f"Error processing fills to trades: {e}")
            return pd.DataFrame()
