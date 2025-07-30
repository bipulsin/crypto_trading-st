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
from config import BASE_URL, API_KEY, API_SECRET, SYMBOL_ID, SYMBOL, LIVE_BASE_URL

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
        
        # State Management
        self.current_position = None
        self.current_orders = {}
        self.last_supertrend_direction = None
        self.order_timeout_counter = {}
        self.iteration_count = 0
        
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
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'supertrend_bot_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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
        """Make authenticated API request"""
        timestamp = str(int(time.time()))
        path = f'/v2{endpoint}'
        url = f'{self.base_url}{path}'
        
        # Prepare body for signature
        body = ""
        if data:
            body = json.dumps(data)
        
        # Create signature message (method + timestamp + path + body)
        message = method + timestamp + path + body
        signature = self.generate_signature(self.api_secret, message)
        
        headers = {
            'api-key': self.api_key,
            'timestamp': timestamp,
            'signature': signature,
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return {'success': False, 'error': str(e)}

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
        response = self.make_request('GET', '/wallet/balances')
        
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
        path = f"/v2/positions?product_id={self.product_id}"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        
        try:
            url = f"{self.base_url}{path}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
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
        path = f"/v2/orders?product_ids={self.product_id}&states=open,pending"
        headers, timestamp, message, signature = self.sign_request("GET", path)
        
        try:
            url = f"{self.base_url}{path}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
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
        """Calculate position size based on available balance"""
        # Use 50% of available balance
        trade_amount = balance * self.position_size_pct
        
        # BTCUSD contract value is 0.001 BTC per contract
        # Position size = trade_amount / price (since we're trading in USD)
        position_size = int(trade_amount / price)
        
        # Minimum position size is 1 contract
        position_size = max(1, position_size)
        
        self.logger.info(f"Calculated position size: {position_size} contracts for ${trade_amount:.2f}")
        return position_size

    def place_market_order(self, side: str, size: int, stop_loss: float = None, take_profit: float = None) -> Optional[Dict]:
        """Place market order with optional stop loss and take profit"""
        order_data = {
            'product_id': self.product_id,
            'size': size,
            'side': side,
            'order_type': 'market_order'
        }
        
        # Add bracket orders for SL and TP if provided
        if stop_loss and take_profit:
            order_data.update({
                'bracket_stop_loss_price': str(stop_loss),
                'bracket_stop_loss_limit_price': str(stop_loss),
                'bracket_take_profit_price': str(take_profit),
                'bracket_take_profit_limit_price': str(take_profit),
                'bracket_stop_trigger_method': 'mark_price'
            })
        
        response = self.make_request('POST', '/orders', data=order_data)
        
        if response.get('success', False):
            order = response.get('result')
            self.logger.info(f"Order placed successfully: {side} {size} contracts at market price")
            if stop_loss:
                self.logger.info(f"Stop Loss: {stop_loss}")
            if take_profit:
                self.logger.info(f"Take Profit: {take_profit}")
            return order
        else:
            self.logger.error(f"Failed to place order: {response}")
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
        
        response = self.make_request('POST', '/orders', data=order_data)
        
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
        
        response = self.make_request('DELETE', '/orders', data=order_data)
        
        if response.get('success', False):
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
        else:
            self.logger.error(f"Failed to cancel order {order_id}: {response}")
            return False

    def update_stop_loss(self, new_sl_price: float):
        """Update stop loss for current position using bracket orders"""
        position = self.get_current_position()
        if not position:
            self.logger.warning("No position found to update stop loss")
            return
        
        # Create new bracket order for the position
        bracket_data = {
            'product_id': self.product_id,
            'stop_loss_order': {
                'order_type': 'market_order',
                'stop_price': str(new_sl_price)
            },
            'bracket_stop_trigger_method': 'mark_price'
        }
        
        response = self.make_request('POST', '/orders/bracket', data=bracket_data)
        
        if response.get('success', False):
            self.logger.info(f"Stop loss updated to: {new_sl_price}")
        else:
            self.logger.error(f"Failed to update stop loss: {response}")

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
                        
                        order = self.place_market_order(side, size, stop_loss, take_profit)
                        if order:
                            self.order_timeout_counter[order['id']] = 0
            
            else:
                # Case 2: Position exists but SuperTrend unchanged - Update moving SL
                self.logger.info("SuperTrend unchanged. Updating stop loss.")
                self.update_stop_loss(supertrend_value)
        
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
                    order = self.place_market_order(side, size, stop_loss, take_profit)
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
                                    
                                    new_order = self.place_market_order(side, size, stop_loss, take_profit)
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
            next_candle = next_candle.replace(hour=next_candle.hour + 1, minute=0)
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

def main():
    """Main function to start the bot"""
    try:
        bot = DeltaExchangeBot()
        bot.run()
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
