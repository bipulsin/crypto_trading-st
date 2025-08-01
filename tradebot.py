import requests
import pandas as pd
import pandas_ta as ta
import time
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Optional
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
        self.leverage = LEVERAGE  # Use leverage from config
        
        # State Management
        self.last_supertrend_direction = None
        self.order_timeout_counter = {}
        self.iteration_count = 0
        
        # Trailing Stop Loss Configuration (fallback)
        self.trailing_stop_distance = 100  # 100 points trailing distance (fallback)
        
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
        """Get current position for BTCUSD with improved detection"""
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
            
            # More thorough position checking
            if position:
                size = position.get('size', 0)
                if size != 0:
                    self.logger.info(f"Current position: Size={size}, Entry={position.get('entry_price')}, PnL={position.get('unrealized_pnl')}")
                    return position
                else:
                    self.logger.info("Position exists but size is 0 (closed position)")
                    return None
            else:
                self.logger.info("No position data returned from API")
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
        """Place market order with bracket trailing stop loss based on SuperTrend difference"""
        order_data = {
            'product_id': self.product_id,
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
            
            order_data.update({
                # 'bracket_stop_loss_price': str(stop_loss),
                # 'bracket_stop_loss_limit_price': str(stop_loss),
                # 'bracket_take_profit_price': str(take_profit),
                # 'bracket_take_profit_limit_price': str(take_profit),
                # 'bracket_stop_trigger_method': 'mark_price',
                # 'bracket_stop_loss_trailing': True,  # Enable native trailing stop loss
                # 'bracket_stop_loss_trailing_distance': trailing_distance,  # Dynamic trailing distance

#-----------------------changed by Bipul
                # Bracket trailing stop loss parameters
                "bracket_trail_amount": str(bracket_trail_amount),
                "bracket_stop_trigger_method": "mark_price",
                # Bracket take profit parameters  
                "bracket_take_profit_price": str(take_profit),
                "bracket_take_profit_limit_price": str(take_profit)  # Market order for TP
#--------------------------------
            })
            self.logger.info(f"Placing bracket order with trailing stop loss distance: {trailing_distance} (trail amount: {bracket_trail_amount})")
        
        # Validate order data before sending
        if not self.validate_order_data(order_data):
            self.logger.error("Order data validation failed for market order")
            return None
        
        response = self.make_request('POST', '/v2/orders', data=order_data)
        
        if response.get('success', False):
            order = response.get('result')
            self.logger.info(f"Order placed successfully: {side} {size} contracts at market price")
            if stop_loss:
                self.logger.info(f"Stop Loss: {stop_loss} (with trailing distance: {trailing_distance})")
            if take_profit:
                self.logger.info(f"Take Profit: {take_profit}")
            
            return order
        else:
            # Check for bracket order position exists error
            error_msg = str(response)
            if 'bracket_order_position_exists' in error_msg:
                self.logger.warning("Bracket order failed - position may exist. Trying simple market order...")
                
                # Try placing simple market order without bracket orders
                simple_order_data = {
                    'product_id': self.product_id,
                    'size': size,
                    'side': side,
                    'order_type': 'market_order'
                }
                
                simple_response = self.make_request('POST', '/v2/orders', data=simple_order_data)
                
                if simple_response.get('success', False):
                    order = simple_response.get('result')
                    self.logger.info(f"Simple market order placed successfully: {side} {size} contracts")
                    self.logger.warning("Bracket orders not available - position may already exist")
                    return order
                else:
                    self.logger.error(f"Failed to place simple market order: {simple_response}")
                    return None
            else:
                self.logger.error(f"Failed to place order: {response}")
                # Log the order data that failed
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
        
        # Double-check position existence with more detailed logging
        if position:
            self.logger.info(f"Position detected: Size={position.get('size')}, Entry={position.get('entry_price')}")
        else:
            self.logger.info("No position detected")
        
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
                    
                    # Double-check position is closed before placing new order
                    position_check = self.get_current_position()
                    if position_check:
                        self.logger.warning("Position still exists after close attempt, waiting longer...")
                        time.sleep(3)
                        position_check = self.get_current_position()
                        if position_check:
                            self.logger.error("Position still exists after extended wait, skipping new order placement")
                            return
                    
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
                        self.logger.error("Failed to place bracket order")
            
            else:
                # Case 4: Check for order timeout (3 iterations) or cancel existing orders
                self.logger.info(f"Found {len(open_orders)} existing orders. Checking for timeouts or cancelling to place new bracket orders.")
                
                # Cancel all existing orders to allow new bracket orders
                for order in open_orders:
                    order_id = order['id']
                    self.logger.info(f"Cancelling existing order {order_id} to place new bracket order")
                    
                    if self.cancel_order(order_id):
                        self.logger.info(f"Successfully cancelled order {order_id}")
                        if order_id in self.order_timeout_counter:
                            del self.order_timeout_counter[order_id]
                    else:
                        self.logger.warning(f"Failed to cancel order {order_id}")
                
                # Wait a moment for orders to be cancelled
                time.sleep(2)
                
                # Now try to place new bracket order
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
                    
                    self.logger.info(f"Placing new {side} bracket order after cancelling existing orders")
                    new_order = self.place_market_order(side, size, stop_loss, take_profit, current_price)
                    if new_order:
                        self.order_timeout_counter[new_order['id']] = 0
                    else:
                        self.logger.error("Failed to place bracket order after cancelling existing orders")

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
