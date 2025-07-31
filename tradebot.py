import requests
import pandas as pd
import pandas_ta as ta
import time
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import threading
from typing import Dict, List, Optional, Tuple
from config import BASE_URL, API_KEY, API_SECRET, SYMBOL_ID, SYMBOL, LIVE_BASE_URL, LEVERAGE

# Load environment variables
load_dotenv()

class DeltaExchangeBot:
    def __init__(self):
        # API Configuration - Use config values
        self.base_url = BASE_URL  # For trading operations (authenticated)
        self.live_base_url = LIVE_BASE_URL  # For market data (no auth needed)
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        
        # Trading Configuration
        self.symbol = SYMBOL
        self.product_id = SYMBOL_ID
        self.resolution = '5m'
        
        # SuperTrend Parameters
        self.st_period = 10
        self.st_multiplier = 3
        
        # Risk Management
        self.position_size_pct = 0.5  # 50% of available balance
        self.take_profit_multiplier = 1.5  # 1.5x risk-reward
        self.max_loss_pct = 0.3  # 30% max loss of position
        self.leverage = LEVERAGE  # Use leverage from config
        
        # State Management
        self.current_position = None
        self.current_orders = {}
        self.last_supertrend_direction = None
        self.order_timeout_counter = {}
        self.iteration_count = 0
        
        # Trailing Stop Loss Configuration (for native API)
        self.trailing_stop_distance = 100  # 100 points trailing distance
        
        # Setup logging
        self.setup_logging()
        
        # Validate credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("API_KEY and API_SECRET must be set in environment variables")
        
        self.logger.info("Delta Exchange SuperTrend Bot initialized")
        self.logger.info(f"Trading Symbol: {self.symbol}")
        self.logger.info(f"SuperTrend Parameters: Period={self.st_period}, Multiplier={self.st_multiplier}")

    def setup_logging(self):
        """Setup comprehensive logging"""
        # Create log filename with current date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'supertrend_bot_{timestamp}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Log file created: {log_filename}")

    def generate_signature(self, secret: str, message: str) -> str:
        """Generate HMAC signature for API authentication"""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def sign_request(self, method, path, body=None):
        """Sign request for trading operations (matches delta_api.py)"""
        timestamp = str(int(time.time()))
        if body is None:
            body = ""
        else:
            body = json.dumps(body)
        message = method + timestamp + path + body
        signature = hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        headers = {
            "api-key": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json"
        }
        return headers, timestamp, message, signature

    def make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
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
                
                body = ""
                if data:
                    body = json.dumps(data)
                
                message = method + timestamp + path + body
                signature = self.generate_signature(self.api_secret, message)
                
                headers = {
                    "api-key": self.api_key,
                    "timestamp": timestamp,
                    "signature": signature,
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}{path}"
                self.logger.info(f"API Request (attempt {attempt + 1}/{max_retries}): {method} {url}")
                
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=15)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=data, timeout=15)
                elif method == 'PUT':
                    response = requests.put(url, headers=headers, json=data, timeout=15)
                elif method == 'DELETE':
                    # For DELETE requests, send data in the request body if provided
                    if data:
                        response = requests.delete(url, headers=headers, json=data, timeout=15)
                    else:
                        response = requests.delete(url, headers=headers, timeout=15)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                self.logger.info(f"Response status: {response.status_code}")
                
                # Handle different response status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 504:
                    # Gateway timeout - retry with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        self.logger.warning(f"504 Gateway Timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"504 Gateway Timeout after {max_retries} attempts")
                        return {'success': False, 'error': f'504 Server Error: Gateway Timeout for url: {url}'}
                elif response.status_code == 429:
                    # Rate limit - wait longer
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (3 ** attempt)
                        self.logger.warning(f"429 Rate Limited, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"429 Rate Limited after {max_retries} attempts")
                        return {'success': False, 'error': f'429 Rate Limited for url: {url}'}
                else:
                    # Other errors - don't retry
                    self.logger.error(f"API request failed: {response.status_code} {response.text}")
                    return {'success': False, 'error': f'{response.status_code} Client Error: {response.reason} for url: {url}'}
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    self.logger.warning(f"Request timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Request timeout after {max_retries} attempts")
                    return {'success': False, 'error': f'Request timeout for url: {url}'}
            except Exception as e:
                self.logger.error(f"Unexpected error in API request: {e}")
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}

    def get_ohlc_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLC data from Delta Exchange (no authentication required)"""
        end_time = int(time.time())
        start_time = end_time - (limit * 5 * 60)  # 5 minutes per candle
        
        params = {
            'resolution': self.resolution,
            'symbol': self.symbol,
            'start': start_time,
            'end': end_time
        }
        
        url = f"{self.live_base_url}/v2/history/candles"
        
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                self.logger.error(f"Failed to fetch OHLC data: {data}")
                return pd.DataFrame()
            
            candle_data = data.get('result', [])
            if not candle_data:
                self.logger.warning("No OHLC data received")
                return pd.DataFrame()
            
            df = pd.DataFrame(candle_data)
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            self.logger.info(f"Fetched {len(df)} OHLC candles")
            return df
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch OHLC data: {e}")
            return pd.DataFrame()

    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SuperTrend indicator using pandas_ta"""
        if len(df) < self.st_period:
            self.logger.warning(f"Insufficient data for SuperTrend calculation. Need {self.st_period}, got {len(df)}")
            return df
        
        try:
            # Calculate SuperTrend
            supertrend = ta.supertrend(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                length=self.st_period,
                multiplier=self.st_multiplier
            )
            
            # Debug: Log the actual column names returned by pandas_ta
            self.logger.info(f"SuperTrend columns: {list(supertrend.columns)}")
            
            # The pandas_ta supertrend function returns columns with different naming
            # Let's find the correct column names
            supertrend_cols = [col for col in supertrend.columns if 'SUPERT' in col]
            direction_cols = [col for col in supertrend.columns if 'SUPERTd' in col]
            
            if not supertrend_cols or not direction_cols:
                self.logger.error(f"SuperTrend columns not found. Available columns: {list(supertrend.columns)}")
                return df
            
            # Use the first found columns
            supertrend_col = supertrend_cols[0]
            direction_col = direction_cols[0]
            
            self.logger.info(f"Using SuperTrend columns: {supertrend_col}, {direction_col}")
            
            # Add the SuperTrend data to the dataframe
            df['supertrend_value'] = supertrend[supertrend_col]
            df['trend_direction'] = supertrend[direction_col]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating SuperTrend: {e}")
            return df

    def get_wallet_balance(self) -> float:
        """Get available wallet balance in USD"""
        response = self.make_request('GET', '/v2/wallet/balances')
        
        if not response.get('success', False):
            self.logger.error(f"Failed to fetch wallet balance: {response}")
            return 0.0
        
        balances = response.get('result', [])
        for balance in balances:
            if balance.get('asset_symbol') == 'USD':
                available = float(balance.get('available_balance', 0))
                self.logger.info(f"Available USD balance: {available}")
                return available
        
        self.logger.warning("USD balance not found")
        return 0.0

    def get_current_position(self) -> Optional[Dict]:
        """Get current position for BTCUSD"""
        # Add small delay to prevent rate limiting
        time.sleep(0.1)
        
        path = f"/v2/positions?product_id={self.product_id}"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        
        try:
            url = f"{self.base_url}{path}"
            self.logger.info(f"Fetching position from: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            self.logger.info(f"Position response status: {response.status_code}")
            if response.status_code != 200:
                self.logger.error(f"Position response text: {response.text}")
                return None
                
            data = response.json()
            
            if not data.get('success', False):
                self.logger.error(f"Failed to fetch position: {data}")
                return None
            
            position = data.get('result')
            if position and position.get('size', 0) != 0:
                self.logger.info(f"Current position: Size={position.get('size')}, Entry={position.get('entry_price')}")
                return position
            
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch position: {e}")
            return None

    def get_open_orders(self) -> List[Dict]:
        """Get open orders for BTCUSD"""
        # Add small delay to prevent rate limiting
        time.sleep(0.1)
        
        path = f"/v2/orders?product_ids={self.product_id}&states=open,pending"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        
        try:
            url = f"{self.base_url}{path}"
            self.logger.info(f"Fetching orders from: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            self.logger.info(f"Orders response status: {response.status_code}")
            if response.status_code != 200:
                self.logger.error(f"Orders response text: {response.text}")
                return []
                
            data = response.json()
            
            if not data.get('success', False):
                self.logger.error(f"Failed to fetch orders: {data}")
                return []
            
            orders = data.get('result', [])
            self.logger.info(f"Found {len(orders)} open orders")
            return orders
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch orders: {e}")
            return []

    def calculate_position_size(self, price: float, balance: float) -> int:
        """Calculate position size based on available balance with leverage"""
        # Use 50% of available balance
        trade_amount = balance * self.position_size_pct
        
        # With 50x leverage, we can control 50x more value than our capital
        # Position value = trade_amount * leverage
        position_value = trade_amount * self.leverage
        
        # For Delta Exchange BTCUSD contracts:
        # 1 lot = 0.001 BTC
        # Position size in lots = position_value / (price * 0.001)
        # This gives us the number of 0.001 BTC lots we can buy with our position value
        position_size = int(position_value / (price * 0.001))
        
        # Minimum position size is 1 lot
        position_size = max(1, position_size)
        
        # Calculate actual notional value
        actual_notional = position_size * price * 0.001
        
        self.logger.info(f"Balance: ${balance:.2f}, Trade amount (50%): ${trade_amount:.2f}")
        self.logger.info(f"Position value with {self.leverage}x leverage: ${position_value:.2f}")
        self.logger.info(f"Calculated position size: {position_size} lots (${actual_notional:.2f} notional value)")
        return position_size

    def place_market_order(self, side: str, size: int, stop_loss: float = None, take_profit: float = None, current_price: float = None) -> Optional[Dict]:
        """Place market order with optional stop loss and take profit using native trailing stop loss"""
        order_data = {
            'product_id': self.product_id,
            'size': size,
            'side': side,
            'order_type': 'market_order'
        }
        
        # Add bracket orders with native trailing stop loss if provided
        if stop_loss and take_profit:
            order_data.update({
                'bracket_stop_loss_price': str(stop_loss),
                'bracket_stop_loss_limit_price': str(stop_loss),
                'bracket_take_profit_price': str(take_profit),
                'bracket_take_profit_limit_price': str(take_profit),
                'bracket_stop_trigger_method': 'mark_price',
                'bracket_stop_loss_trailing': True,  # Enable native trailing stop loss
                'bracket_stop_loss_trailing_distance': self.trailing_stop_distance,  # 100 points trailing distance
            })
            self.logger.info("Placing bracket order with native trailing stop loss")
        
        # Validate order data before sending
        if not self.validate_order_data(order_data):
            self.logger.error("Order data validation failed for market order")
            return None
        
        response = self.make_request('POST', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            order = response.get('result')
            self.logger.info(f"Order placed successfully: {side} {size} contracts at market price")
            if stop_loss:
                self.logger.info(f"Stop Loss: {stop_loss} (with native trailing)")
            if take_profit:
                self.logger.info(f"Take Profit: {take_profit}")
            
            return order
        else:
            self.logger.error(f"Failed to place order: {response}")
            # Log the order data that failed
            self.logger.error(f"Failed order data: {order_data}")
            return None

    def place_limit_order(self, side: str, size: int, price: float, stop_loss: float = None, take_profit: float = None) -> Optional[Dict]:
        """Place limit order with optional stop loss and take profit using native trailing stop loss"""
        order_data = {
            'product_id': self.product_id,
            'size': size,
            'side': side,
            'order_type': 'limit_order',
            'limit_price': str(price)
        }
        
        # Add bracket orders with native trailing stop loss if provided
        if stop_loss and take_profit:
            order_data.update({
                'bracket_stop_loss_price': str(stop_loss),
                'bracket_stop_loss_limit_price': str(stop_loss),
                'bracket_take_profit_price': str(take_profit),
                'bracket_take_profit_limit_price': str(take_profit),
                'bracket_stop_trigger_method': 'mark_price',
                'bracket_stop_loss_trailing': True,  # Enable native trailing stop loss
                'bracket_stop_loss_trailing_distance': self.trailing_stop_distance,  # 100 points trailing distance
            })
            self.logger.info("Placing bracket limit order with native trailing stop loss")
        
        # Validate order data before sending
        if not self.validate_order_data(order_data):
            self.logger.error("Order data validation failed for limit order")
            return None
        
        response = self.make_request('POST', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            order = response.get('result')
            self.logger.info(f"Limit order placed successfully: {side} {size} contracts at {price}")
            if stop_loss:
                self.logger.info(f"Stop Loss: {stop_loss} (with native trailing)")
            if take_profit:
                self.logger.info(f"Take Profit: {take_profit}")
            
            return order
        else:
            self.logger.error(f"Failed to place limit order: {response}")
            self.logger.error(f"Failed order data: {order_data}")
            return None

    def close_position(self) -> bool:
        """Close current position with market order"""
        position = self.get_current_position()
        if not position:
            self.logger.info("No position to close")
            return True
        
        size = abs(position.get('size', 0))
        side = 'sell' if position.get('size', 0) > 0 else 'buy'
        
        order_data = {
            'product_id': self.product_id,
            'size': size,
            'side': side,
            'order_type': 'market_order',
            'reduce_only': 'true'
        }
        
        response = self.make_request('POST', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            self.logger.info(f"Position closed: {side} {size} contracts")
            return True
        else:
            self.logger.error(f"Failed to close position: {response}")
            return False

    def cancel_order(self, order_id: int) -> bool:
        """Cancel specific order"""
        order_data = {
            'id': order_id,
            'product_id': self.product_id
        }
        
        response = self.make_request('DELETE', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
        else:
            # Check if the error is because the order doesn't exist
            error_msg = response.get('error', '')
            if 'open_order_not_found' in error_msg or '404' in error_msg:
                self.logger.info(f"Order {order_id} not found (may already be cancelled/filled)")
                return True  # Consider this a success since the goal is achieved
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {response}")
                return False

    def update_stop_loss(self, new_sl_price: float):
        """Update stop loss for current position by modifying existing orders"""
        # First, get current open orders
        open_orders = self.get_open_orders()
        if not open_orders:
            self.logger.warning("No open orders found to update stop loss")
            return
        
        # Find orders that have stop loss
        # Look for orders with stop_order_type="stop_loss_order" or bracket_stop_loss_price
        orders_with_sl = [order for order in open_orders if 
                         order.get('stop_order_type') == 'stop_loss_order' or
                         order.get('stop_loss') is not None or 
                         order.get('bracket_stop_loss_price') is not None]
        
        if not orders_with_sl:
            self.logger.warning("No orders with stop loss found to update")
            return
        
        # Check if we have an open position - if so, we can't create new bracket orders
        position = self.get_current_position()
        has_position = position is not None and abs(position.get('size', 0)) > 0
        
        if has_position:
            self.logger.info("Position exists - will use stop orders instead of bracket orders")
        
        # Try to use edit_bracket_order first for bracket orders
        success_count = 0
        for order in orders_with_sl:
            order_id = order.get('id')
            if not order_id:
                continue
            
            # Check if this is a bracket order
            is_bracket_order = order.get('bracket_order') or order.get('bracket_stop_loss_price') is not None
            
            if is_bracket_order and not has_position:
                # Try to edit the bracket order directly first
                self.logger.info(f"Attempting to edit bracket order {order_id} stop loss to {new_sl_price}")
                
                # Use PUT request to edit the order - use the correct endpoint from delta_api.py
                edit_data = {
                    'stop_loss': new_sl_price
                }
                
                # Use the correct endpoint for editing orders (same as delta_api.py)
                edit_response = self.make_request('PUT', f'/v2/orders/{order_id}', data=edit_data)
                
                if edit_response.get('success', False):
                    self.logger.info(f"Successfully edited bracket order {order_id} stop loss to {new_sl_price}")
                    success_count += 1
                    continue
                else:
                    self.logger.warning(f"Failed to edit bracket order {order_id}, falling back to cancel-and-replace: {edit_response}")
            
            # Fallback to cancel-and-replace approach
            order_side = order.get('side')
            order_size = order.get('size')
            stop_trigger_method = order.get('stop_trigger_method', 'mark_price')
            
            # Cancel the existing order
            cancel_data = {
                'id': order_id,
                'product_id': self.product_id
            }
            
            cancel_response = self.make_request('DELETE', '/v2/orders', data=cancel_data)
            
            if cancel_response.get('success', False):
                self.logger.info(f"Cancelled order {order_id} for stop loss update")
                
                # If we have a position, create a simple stop order instead of bracket order
                if has_position:
                    # Determine the correct stop loss side based on current position
                    position = self.get_current_position()
                    if position:
                        position_size = position.get('size', 0)
                        stop_loss_side = self.get_stop_loss_side(position_size)
                        
                        self.logger.info(f"Position size: {position_size}, using stop loss side: {stop_loss_side}")
                        
                        # Use the helper method to create stop loss order with correct side
                        new_order = self.place_stop_loss_order(stop_loss_side, abs(position_size), new_sl_price)
                        if new_order:
                            self.logger.info(f"Created stop loss order {new_order.get('id')} at price: {new_sl_price}")
                            success_count += 1
                        else:
                            self.logger.error(f"Failed to create stop loss order for position")
                    else:
                        self.logger.error("Position not found when trying to create stop loss order")
                        
                elif is_bracket_order:
                    # Use the helper method to recreate bracket order (only when no position exists)
                    new_order = self.recreate_bracket_order(order, new_sl_price)
                    if new_order:
                        self.logger.info(f"Replaced bracket order {order_id} with new order {new_order.get('id')} at stop loss: {new_sl_price}")
                        success_count += 1
                    else:
                        self.logger.error(f"Failed to recreate bracket order {order_id}")
                        
                else:
                    # For regular stop loss orders, use limit order with stop_price
                    new_order_data = {
                        'product_id': self.product_id,
                        'size': order_size,
                        'side': order_side,
                        'order_type': 'limit_order',
                        'stop_price': str(new_sl_price),
                        'limit_price': str(new_sl_price),
                        'stop_trigger_method': stop_trigger_method,
                        'reduce_only': 'true'
                    }
                    
                    new_order_response = self.make_request('POST', '/v2/orders', data=new_order_data)
                    
                    if new_order_response.get('success', False):
                        new_order = new_order_response.get('result')
                        self.logger.info(f"Replaced order {order_id} with new stop loss order {new_order.get('id')} at price: {new_sl_price}")
                        success_count += 1
                    else:
                        self.logger.error(f"Failed to place replacement order: {new_order_response}")
                        self.logger.error(f"Order data that failed: {new_order_data}")
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {cancel_response}")
        
        if success_count > 0:
            self.logger.info(f"Successfully updated stop loss for {success_count} orders to: {new_sl_price}")
        else:
            self.logger.error("Failed to update stop loss for any orders")

    def recreate_bracket_order(self, original_order: Dict, new_sl_price: float) -> Optional[Dict]:
        """Recreate a bracket order with updated stop loss after cancellation"""
        try:
            order_side = original_order.get('side')
            order_size = original_order.get('size')
            take_profit_price = original_order.get('bracket_take_profit_price')
            limit_price = original_order.get('limit_price')
            stop_trigger_method = original_order.get('stop_trigger_method', 'mark_price')
            
            # Validate required fields
            if not order_side or not order_size:
                self.logger.error(f"Missing required fields for bracket order recreation: side={order_side}, size={order_size}")
                return None
            
            # Create new bracket order data
            new_order_data = {
                'product_id': self.product_id,
                'size': order_size,
                'side': order_side,
                'order_type': 'limit_order',
                'bracket_stop_loss_price': str(new_sl_price),
                'bracket_stop_loss_limit_price': str(new_sl_price),
                'bracket_stop_trigger_method': stop_trigger_method,
                'reduce_only': 'true'
            }
            
            # Add limit price if it exists
            if limit_price:
                new_order_data['limit_price'] = str(limit_price)
            
            # Add take profit if it exists - this is crucial for bracket orders
            if take_profit_price:
                new_order_data['bracket_take_profit_price'] = str(take_profit_price)
                new_order_data['bracket_take_profit_limit_price'] = str(take_profit_price)
            else:
                # If no take profit in original order, we need to calculate one
                # Get current market price to calculate a reasonable take profit
                df = self.get_ohlc_data(limit=5)
                if not df.empty:
                    current_price = float(df.iloc[-1]['close'])
                    # Calculate take profit based on risk-reward ratio
                    risk = abs(current_price - new_sl_price)
                    take_profit = current_price + (risk * self.take_profit_multiplier)
                    new_order_data['bracket_take_profit_price'] = str(take_profit)
                    new_order_data['bracket_take_profit_limit_price'] = str(take_profit)
                    self.logger.info(f"Calculated take profit: {take_profit} based on risk: {risk}")
            
            # Remove None values
            new_order_data = {k: v for k, v in new_order_data.items() if v is not None}
            
            self.logger.info(f"Recreating bracket order with data: {new_order_data}")
            
            # Validate order data before sending
            if not self.validate_order_data(new_order_data):
                self.logger.error("Order data validation failed")
                return None
            
            response = self.make_request('POST', '/v2/orders', data=new_order_data)
            
            if response.get('success', False):
                new_order = response.get('result')
                self.logger.info(f"Successfully recreated bracket order {new_order.get('id')} with stop loss: {new_sl_price}")
                return new_order
            else:
                self.logger.error(f"Failed to recreate bracket order: {response}")
                # Log the specific error for debugging
                error_msg = response.get('error', '')
                if 'bracket_order_position_exists' in error_msg:
                    self.logger.error("Cannot create bracket order when position exists - use stop orders instead")
                return None
                
        except Exception as e:
            self.logger.error(f"Error recreating bracket order: {e}")
            return None

    def validate_order_data(self, order_data: Dict) -> bool:
        """Validate order data before placing"""
        required_fields = ['product_id', 'size', 'side', 'order_type']
        
        for field in required_fields:
            if field not in order_data or order_data[field] is None:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Validate size is positive
        try:
            size = int(order_data['size'])
            if size <= 0:
                self.logger.error(f"Invalid size: {size}")
                return False
        except (ValueError, TypeError):
            self.logger.error(f"Invalid size format: {order_data['size']}")
            return False
        
        # Validate side is valid
        if order_data['side'] not in ['buy', 'sell']:
            self.logger.error(f"Invalid side: {order_data['side']}")
            return False
        
        # Validate prices are numeric if present
        price_fields = ['limit_price', 'bracket_stop_loss_price', 'bracket_take_profit_price']
        for field in price_fields:
            if field in order_data and order_data[field] is not None:
                try:
                    float(order_data[field])
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid price format for {field}: {order_data[field]}")
                    return False
        
        return True

    def place_stop_loss_order(self, side: str, size: int, stop_price: float) -> Optional[Dict]:
        """Place a simple stop loss order for an existing position"""
        try:
            # For Delta Exchange, we need to use limit_order with stop_price for stop loss
            order_data = {
                'product_id': self.product_id,
                'size': size,
                'side': side,
                'order_type': 'limit_order',
                'stop_price': str(stop_price),
                'limit_price': str(stop_price),
                'stop_trigger_method': 'mark_price',
                'reduce_only': 'true'
            }
            
            # Validate order data before sending
            if not self.validate_order_data(order_data):
                self.logger.error("Order data validation failed for stop loss order")
                return None
            
            response = self.make_request('POST', '/v2/orders', data=order_data)
            
            if response.get('success', False):
                order = response.get('result')
                self.logger.info(f"Stop loss order placed successfully: {side} {size} contracts at {stop_price}")
                return order
            else:
                self.logger.error(f"Failed to place stop loss order: {response}")
                self.logger.error(f"Failed order data: {order_data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing stop loss order: {e}")
            return None

    def get_stop_loss_side(self, position_size: int) -> str:
        """Determine the correct stop loss side based on position size"""
        if position_size > 0:
            return 'sell'  # Close long position
        else:
            return 'buy'   # Close short position



    def log_current_state(self):
        """Log current state of orders and positions for debugging"""
        try:
            position = self.get_current_position()
            open_orders = self.get_open_orders()
            
            self.logger.info("=== Current State ===")
            
            if position:
                self.logger.info(f"Position: Size={position.get('size')}, Entry={position.get('entry_price')}, PnL={position.get('unrealized_pnl')}")
                self.logger.info("Trailing stop loss is handled by the exchange automatically")
            else:
                self.logger.info("No open position")
            
            if open_orders:
                self.logger.info(f"Open Orders ({len(open_orders)}):")
                for order in open_orders:
                    order_info = f"  ID: {order.get('id')}, Side: {order.get('side')}, Size: {order.get('size')}, Type: {order.get('order_type')}, State: {order.get('state')}"
                    if order.get('bracket_stop_loss_price'):
                        order_info += f", SL: {order.get('bracket_stop_loss_price')}"
                    if order.get('bracket_take_profit_price'):
                        order_info += f", TP: {order.get('bracket_take_profit_price')}"
                    self.logger.info(order_info)
            else:
                self.logger.info("No open orders")
            
            self.logger.info("===================")
            
        except Exception as e:
            self.logger.error(f"Error logging current state: {e}")

    def execute_trading_logic(self, df: pd.DataFrame):
        """Main trading logic execution"""
        if len(df) < 2:
            self.logger.warning("Insufficient data for trading logic")
            return
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        current_trend = current_candle['trend_direction']
        previous_trend = previous_candle['trend_direction']
        current_price = current_candle['close']
        supertrend_value = current_candle['supertrend_value']
        
        self.logger.info(f"Current price: {current_price}, SuperTrend: {supertrend_value}, Direction: {current_trend}")
        
        # Get current position and orders
        position = self.get_current_position()
        open_orders = self.get_open_orders()
        
        # Check if SuperTrend direction changed
        trend_changed = (previous_trend != current_trend) if self.last_supertrend_direction is not None else False
        
        # Update last SuperTrend direction
        self.last_supertrend_direction = current_trend
        
        # Trading Logic Implementation
        if position:
            # Case 1 & 2: Position exists
            position_side = 'long' if position.get('size', 0) > 0 else 'short'
            
            # Native trailing stop loss is handled by the exchange automatically
            
            if trend_changed:
                # Case 1: Position exists and SuperTrend changed - Close and reverse
                self.logger.info(f"SuperTrend changed from {previous_trend} to {current_trend}. Closing position and reversing.")
                
                if self.close_position():
                    time.sleep(2)  # Wait for position to close
                    

                    
                    # Place new order in opposite direction
                    balance = self.get_wallet_balance()
                    if balance > 0:
                        size = self.calculate_position_size(current_price, balance)
                        side = 'buy' if current_trend == 1 else 'sell'
                        
                        # Calculate SL and TP
                        if current_trend == 1:  # Bullish
                            stop_loss = supertrend_value
                            risk = current_price - stop_loss
                            take_profit = current_price + (risk * self.take_profit_multiplier)
                        else:  # Bearish
                            stop_loss = supertrend_value
                            risk = stop_loss - current_price
                            take_profit = current_price - (risk * self.take_profit_multiplier)
                        
                        order = self.place_market_order(side, size, stop_loss, take_profit, current_price)
                        if order:
                            self.order_timeout_counter[order['id']] = 0
            
            else:
                # Case 2: Position exists but SuperTrend unchanged - No action needed
                self.logger.info("SuperTrend unchanged. Keeping existing stop loss orders.")
        
        else:
            # Case 3: No position exists
            if not open_orders:
                
                # Place new order based on SuperTrend direction
                balance = self.get_wallet_balance()
                if balance > 0:
                    size = self.calculate_position_size(current_price, balance)
                    side = 'buy' if current_trend == 1 else 'sell'
                    
                    # Calculate SL and TP
                    if current_trend == 1:  # Bullish
                        stop_loss = supertrend_value
                        risk = current_price - stop_loss
                        take_profit = current_price + (risk * self.take_profit_multiplier)
                    else:  # Bearish
                        stop_loss = supertrend_value
                        risk = stop_loss - current_price
                        take_profit = current_price - (risk * self.take_profit_multiplier)
                    
                    self.logger.info(f"Placing new {side} order based on SuperTrend direction: {current_trend}")
                    order = self.place_market_order(side, size, stop_loss, take_profit, current_price)
                    if order:
                        self.order_timeout_counter[order['id']] = 0
            
            else:
                # Case 4: Check for order timeout (3 iterations)
                for order in open_orders:
                    order_id = order['id']
                    if order_id in self.order_timeout_counter:
                        self.order_timeout_counter[order_id] += 1
                        
                        if self.order_timeout_counter[order_id] >= 3:
                            self.logger.info(f"Order {order_id} timeout reached. Cancelling and placing new order.")
                            
                            if self.cancel_order(order_id):
                                time.sleep(1)
                                

                                
                                # Place new order at current market price
                                balance = self.get_wallet_balance()
                                if balance > 0:
                                    size = self.calculate_position_size(current_price, balance)
                                    side = 'buy' if current_trend == 1 else 'sell'
                                    
                                    # Calculate SL and TP
                                    if current_trend == 1:  # Bullish
                                        stop_loss = supertrend_value
                                        risk = current_price - stop_loss
                                        take_profit = current_price + (risk * self.take_profit_multiplier)
                                    else:  # Bearish
                                        stop_loss = supertrend_value
                                        risk = stop_loss - current_price
                                        take_profit = current_price - (risk * self.take_profit_multiplier)
                                    
                                    new_order = self.place_market_order(side, size, stop_loss, take_profit, current_price)
                                    if new_order:
                                        self.order_timeout_counter[new_order['id']] = 0
                            
                            # Remove old order from timeout counter
                            del self.order_timeout_counter[order_id]
                    else:
                        self.order_timeout_counter[order_id] = 0

    def run_iteration(self):
        """Run single trading iteration"""
        try:
            self.iteration_count += 1
            self.logger.info(f"=== Starting iteration {self.iteration_count} ===")
            
            # Fetch OHLC data
            df = self.get_ohlc_data(limit=50)  # Get enough data for SuperTrend calculation
            
            if df.empty:
                self.logger.error("No OHLC data available")
                return
            
            # Calculate SuperTrend
            df = self.calculate_supertrend(df)
            
            if 'trend_direction' not in df.columns:
                self.logger.error("SuperTrend calculation failed")
                return
            
            # Execute trading logic
            self.execute_trading_logic(df)
            
            self.logger.info(f"=== Iteration {self.iteration_count} completed ===")
            
        except Exception as e:
            self.logger.error(f"Error in iteration {self.iteration_count}: {e}")

    def wait_for_next_candle(self):
        """Wait for next 5-minute candle"""
        now = datetime.now()
        next_candle = now.replace(second=0, microsecond=0)
        
        # Round to next 5-minute interval
        minutes = (next_candle.minute // 5 + 1) * 5
        if minutes >= 60:
            # Use timedelta to safely handle hour overflow
            next_candle = next_candle.replace(minute=0) + timedelta(hours=1)
        else:
            next_candle = next_candle.replace(minute=minutes)
        
        wait_seconds = (next_candle - now).total_seconds()
        
        if wait_seconds > 0:
            self.logger.info(f"Waiting {wait_seconds:.1f} seconds for next candle at {next_candle}")
            time.sleep(wait_seconds)

    def run(self):
        """Main bot execution loop"""
        self.logger.info("Starting SuperTrend Trading Bot")
        
        try:
            # Initial setup - wait for next candle close
            self.wait_for_next_candle()
            
            while True:
                # Run trading iteration
                self.run_iteration()
                
                # Wait for next 5-minute candle
                self.wait_for_next_candle()
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
        finally:
            self.logger.info("SuperTrend Trading Bot shutdown")

    def check_server_health(self) -> bool:
        """Check if the server is responding properly"""
        try:
            # Try a simple market data request first (no auth required)
            url = f"{self.live_base_url}/v2/history/candles"
            params = {
                'symbol': 'BTCUSD',
                'resolution': '5m',
                'limit': 1
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("✅ Market data server is responding")
                return True
            else:
                self.logger.warning(f"⚠️ Market data server issue: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Server health check failed: {e}")
            return False

    def log_server_status(self):
        """Log current server configuration and status"""
        self.logger.info(f"🔧 Server Configuration:")
        self.logger.info(f"   Base URL: {self.base_url}")
        self.logger.info(f"   Live Base URL: {self.live_base_url}")
        self.logger.info(f"   Product ID: {self.product_id}")
        self.logger.info(f"   Symbol: {self.symbol}")
        
        # Check server health
        if self.check_server_health():
            self.logger.info("✅ Server health check passed")
        else:
            self.logger.warning("⚠️ Server health check failed - consider switching to live environment")
            self.logger.info("💡 To switch to live environment, set TRADING_FROM_LIVE = True in config.py")

def main():
    """Main function to start the bot"""
    bot = DeltaExchangeBot()
    
    # Log server status and health check
    bot.log_server_status()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.logger.info("Bot stopped by user")
    except Exception as e:
        bot.logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
