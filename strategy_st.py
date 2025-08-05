import requests
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Optional
from config import BASE_URL, API_KEY, API_SECRET, SYMBOL_ID, SYMBOL, LIVE_BASE_URL, LEVERAGE, ST_WITH_TRAILING
from delta_api import DeltaAPI
from supertrend import calculate_supertrend_enhanced

# Load environment variables
load_dotenv()

class DeltaExchangeBot:
    def __init__(self):
        # Initialize Delta API
        self.api = DeltaAPI()
        
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
        
        # Trailing Stop Loss Configuration
        self.st_with_trailing = ST_WITH_TRAILING  # Use config variable for trailing stop
        self.trailing_stop_distance = 100  # 100 points trailing distance (fallback)
        
        # Setup logging
        self.setup_logging()
        
        # Validate credentials by testing API connection
        self.validate_api_connection()
        
        self.logger.info("Delta Exchange SuperTrend Bot initialized")
        self.logger.info(f"Trading Symbol: {self.symbol}")
        self.logger.info(f"SuperTrend Parameters: Period={self.st_period}, Multiplier={self.st_multiplier}")
        self.logger.info(f"Trailing Stop Configuration: {'Enabled' if self.st_with_trailing else 'Disabled'}")

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

    def get_ohlc_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLC data using delta_api"""
        return self.api.get_ohlc_data(symbol=self.symbol, resolution=self.resolution, limit=limit)

    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SuperTrend using supertrend module"""
        return calculate_supertrend_enhanced(df, self.st_period, self.st_multiplier, self.logger)

    def get_wallet_balance(self) -> float:
        """Get wallet balance using delta_api"""
        return self.api.get_wallet_balance()

    def get_current_position(self) -> Optional[Dict]:
        """Get current position using delta_api"""
        return self.api.get_current_position(self.product_id)

    def get_open_orders(self) -> List[Dict]:
        """Get open orders using delta_api"""
        return self.api.get_open_orders(self.product_id)

    def calculate_position_size(self, price: float, balance: float) -> float:
        """Calculate position size based on balance and risk management"""
        risk_amount = balance * self.position_size_pct
        position_size = (risk_amount * self.leverage) / price
        
        # Ensure minimum position size (0.001 BTC minimum = 1 lot)
        if position_size < 0.001:
            position_size = 0.001
            
        # Round to 3 decimal places for BTC precision
        position_size = round(position_size, 3)
        
        # Multiply by 1000 for order placement (convert BTC to lot units)
        order_size = position_size * 1000
            
        self.logger.info(f"Calculated position size: {position_size} BTC = {order_size} lots (balance: {balance}, price: {price})")
        return order_size

    def place_market_order(self, side: str, size: float, stop_loss: float = None, take_profit: float = None, current_price: float = None) -> Optional[Dict]:
        """Place market order using delta_api"""
        return self.api.place_market_order_with_trailing(
            side=side,
            size=size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=current_price,
            product_id=self.product_id,
            st_with_trailing=self.st_with_trailing
        )

    def close_position(self) -> bool:
        """Close current position using delta_api"""
        return self.api.close_all_positions(self.product_id)

    def cancel_order(self, order_id: int) -> bool:
        """Cancel order using delta_api"""
        return self.api.cancel_order(order_id)

    def validate_order_data(self, order_data: Dict) -> bool:
        """Validate order data using delta_api"""
        return self.api.validate_order_data(order_data)

    def validate_api_connection(self):
        """Validate API credentials by testing connection"""
        try:
            # Test API connection by getting wallet balance
            balance = self.api.get_wallet_balance()
            if balance is not None:
                self.logger.info(f"✅ API connection validated - Balance: {balance}")
            else:
                raise ValueError("Failed to get wallet balance")
        except Exception as e:
            self.logger.error(f"❌ API connection failed: {e}")
            raise ValueError("API_KEY and API_SECRET must be set correctly in environment variables")







    def execute_trading_logic(self, df: pd.DataFrame):
        """Main trading logic execution"""
        if len(df) < 2:
            self.logger.warning("Insufficient data for trading logic")
            return
        
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # Check if SuperTrend columns exist
        if 'trend_direction' not in df.columns or 'supertrend_value' not in df.columns:
            self.logger.error("SuperTrend columns not found in dataframe")
            return
        
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
                # Case 3a: No position and no orders - Place new order based on SuperTrend direction
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
                # Case 3b: No position but existing orders - Skip placing new orders
                # Let existing orders handle the trading, only monitor for timeouts
                self.logger.info(f"Found {len(open_orders)} existing orders but no position. Monitoring existing orders.")
                
                # Only check for order timeouts, don't place new orders
                for order in open_orders:
                    order_id = order['id']
                    if order_id in self.order_timeout_counter:
                        self.order_timeout_counter[order_id] += 1
                        
                        if self.order_timeout_counter[order_id] >= 3:
                            self.logger.info(f"Order {order_id} timeout reached. Cancelling order.")
                            
                            if self.cancel_order(order_id):
                                self.logger.info(f"Successfully cancelled timed out order {order_id}")
                                del self.order_timeout_counter[order_id]
                            else:
                                self.logger.warning(f"Failed to cancel timed out order {order_id}")
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
            
            if 'trend_direction' not in df.columns or 'supertrend_value' not in df.columns:
                self.logger.error("SuperTrend calculation failed - missing required columns")
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
            url = f"{LIVE_BASE_URL}/v2/history/candles"
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
        self.logger.info(f"   Base URL: {BASE_URL}")
        self.logger.info(f"   Live Base URL: {LIVE_BASE_URL}")
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
