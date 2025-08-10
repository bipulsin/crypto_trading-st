import requests
import pandas as pd
import time
import logging
import argparse
import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Get configuration from environment variables (set by strategy manager)
BASE_URL = os.getenv('BASE_URL', 'https://api.delta.exchange')
API_KEY = os.getenv('API_KEY', '')
API_SECRET = os.getenv('API_SECRET', '')
SYMBOL_ID = os.getenv('SYMBOL_ID', '1')
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
LEVERAGE = int(os.getenv('LEVERAGE', '1'))
ST_WITH_TRAILING = os.getenv('ST_WITH_TRAILING', 'false').lower() == 'true'

# Strategy-specific configuration from database
STRATEGY_TAKE_PROFIT_MULTIPLIER = float(os.getenv('STRATEGY_TAKE_PROFIT_MULTIPLIER', '1.5'))
STRATEGY_TRAILING_STOP = os.getenv('STRATEGY_TRAILING_STOP', 'false').lower() == 'true'
STRATEGY_CANDLE_SIZE = os.getenv('STRATEGY_CANDLE_SIZE', '5m')

# Debug: Print environment variables
print(f"=== ENVIRONMENT VARIABLES ===")
print(f"BASE_URL: {BASE_URL}")
print(f"API_KEY: {API_KEY[:10] if API_KEY else 'Not set'}...")
print(f"SYMBOL_ID: {SYMBOL_ID}")
print(f"STRATEGY_CANDLE_SIZE: {STRATEGY_CANDLE_SIZE}")
print(f"STRATEGY_TAKE_PROFIT_MULTIPLIER: {STRATEGY_TAKE_PROFIT_MULTIPLIER}")
print(f"STRATEGY_TRAILING_STOP: {STRATEGY_TRAILING_STOP}")
print("================================")

try:
    from delta_api import DeltaAPI
    from supertrend import calculate_supertrend_enhanced, calculate_supertrend_manual
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

class DeltaExchangeBot:
    def __init__(self, user_id=None, strategy_name=None):
        # Initialize Delta API
        self.api = DeltaAPI()
        
        # Strategy configuration
        self.st_period = ST_PERIOD
        self.st_multiplier = ST_MULTIPLIER
        self.take_profit_multiplier = TAKE_PROFIT_MULTIPLIER
        self.position_size_pct = POSITION_SIZE_PCT
        self.leverage = LEVERAGE
        self.symbol = SYMBOL
        self.product_id = SYMBOL_ID
        self.asset_id = ASSET_ID
        
        # Trailing Stop Loss Configuration
        self.st_with_trailing = STRATEGY_TRAILING_STOP # Use strategy-specific trailing stop
        self.trailing_stop_distance = 100  # 100 points trailing distance (fallback)
        
        # Default capital for fallback when API fails
        self.default_capital = float(os.environ.get('DEFAULT_CAPITAL', '1000.0'))
        
        # Order management
        self.order_timeout_counter = {}
        self.max_order_timeout = 3  # Maximum iterations before cancelling order
        
        # Strategy state
        self.iteration_count = 0
        self.last_trend_change = None
        
        # Setup logging
        self.setup_logging()
        
        # Validate API connection
        self.validate_api_connection()
        
        # Load strategy configuration
        self.load_strategy_config()
        
        # Log initial configuration
        self.logger.info(f"SuperTrend Strategy initialized with period={self.st_period}, multiplier={self.st_multiplier}")
        self.logger.info(f"Trading {self.symbol} (ID: {self.product_id}) with {self.leverage}x leverage")
        self.logger.info(f"Position size: {self.position_size_pct * 100}% of balance, Take profit: {self.take_profit_multiplier}x risk")
        self.logger.info(f"Trailing stop: {'Enabled' if self.st_with_trailing else 'Disabled'}")
        self.logger.info(f"Default capital fallback: ${self.default_capital}")

    def setup_logging(self):
        """Setup comprehensive logging"""
        # Create log filename with current date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_suffix = f"_user_{self.user_id}" if self.user_id else ""
        log_filename = f'supertrend_bot{user_suffix}_{timestamp}.log'
        
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
        
        # Also log to database if strategy manager is available
        try:
            # Add the current directory to Python path to find strategy_manager
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from strategy_manager import strategy_manager
            if strategy_manager and self.user_id:
                # Create a custom handler for database logging
                class DatabaseHandler(logging.Handler):
                    def __init__(self, strategy_manager, user_id, strategy_name):
                        super().__init__()
                        self.strategy_manager = strategy_manager
                        self.user_id = user_id
                        self.strategy_name = strategy_name
                    
                    def emit(self, record):
                        try:
                            # Convert log level to string
                            level = record.levelname
                            message = self.format(record)
                            
                            # Log to database
                            self.strategy_manager.log_strategy_event(
                                self.user_id, 
                                self.strategy_name, 
                                level, 
                                message
                            )
                        except Exception:
                            # Silently fail if database logging fails
                            pass
                
                # Add database handler
                db_handler = DatabaseHandler(strategy_manager, self.user_id, self.strategy_name)
                db_handler.setFormatter(logging.Formatter('%(message)s'))
                self.logger.addHandler(db_handler)
                self.logger.info("Database logging enabled")
        except ImportError as e:
            # Strategy manager not available, continue without database logging
            self.logger.info(f"Database logging not available: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to setup database logging: {e}")

    def get_ohlc_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLC data using delta_api"""
        return self.api.get_ohlc_data(symbol=self.symbol, resolution=self.resolution, limit=limit)

    def calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SuperTrend using supertrend module with fallback"""
        try:
            # Try enhanced calculation first
            result = calculate_supertrend_enhanced(df, self.st_period, self.st_multiplier, self.logger)
            
            # Check if calculation was successful
            if 'trend_direction' in result.columns and 'supertrend_value' in result.columns:
                if not result[['trend_direction', 'supertrend_value']].isnull().all().all():
                    return result
            
            # If enhanced calculation failed, try manual calculation
            self.logger.warning("Enhanced SuperTrend calculation failed, trying manual calculation...")
            result = calculate_supertrend_manual(df, self.st_period, self.st_multiplier, self.logger)
            
            if 'trend_direction' in result.columns and 'supertrend_value' in result.columns:
                if not result[['trend_direction', 'supertrend_value']].isnull().all().all():
                    self.logger.info("Manual SuperTrend calculation successful")
                    return result
            
            # If both methods failed, return original dataframe with error columns
            self.logger.error("Both SuperTrend calculation methods failed")
            result['trend_direction'] = 0
            result['supertrend_value'] = 0
            return result
            
        except Exception as e:
            self.logger.error(f"Error in SuperTrend calculation: {e}")
            # Return original dataframe with default values
            df['trend_direction'] = 0
            df['supertrend_value'] = 0
            return df

    def get_wallet_balance(self) -> float:
        """Get wallet balance using delta_api"""
        try:
            balance = self.api.get_wallet_balance()
            if balance is not None:
                return balance
            else:
                self.logger.warning(f"API returned None for balance. Falling back to default capital: {self.default_capital}")
                return self.default_capital
        except Exception as e:
            self.logger.error(f"Error getting wallet balance from API: {e}. Falling back to default capital: {self.default_capital}")
            return self.default_capital

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
        return round(position_size, 3)

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

    def load_strategy_config(self):
        """Load strategy configuration from database if available"""
        try:
            # This would typically connect to a database to load user-specific strategy settings
            # For now, we'll use environment variables as fallback
            if os.environ.get('STRATEGY_ST_PERIOD'):
                self.st_period = int(os.environ.get('STRATEGY_ST_PERIOD'))
                self.logger.info(f"Updated SuperTrend period from config: {self.st_period}")
            
            if os.environ.get('STRATEGY_ST_MULTIPLIER'):
                self.st_multiplier = float(os.environ.get('STRATEGY_ST_MULTIPLIER'))
                self.logger.info(f"Updated SuperTrend multiplier from config: {self.st_multiplier}")
            
            if os.environ.get('STRATEGY_SYMBOL'):
                self.symbol = os.environ.get('STRATEGY_SYMBOL')
                self.logger.info(f"Updated trading symbol from config: {self.symbol}")
            
            if os.environ.get('STRATEGY_SYMBOL_ID'):
                self.product_id = os.environ.get('STRATEGY_SYMBOL_ID')
                self.logger.info(f"Updated product ID from config: {self.product_id}")
                
        except Exception as e:
            self.logger.warning(f"Could not load strategy configuration: {e}")
            self.logger.info("Using default configuration values")

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
        
        # Validate SuperTrend data
        if pd.isna(current_candle['trend_direction']) or pd.isna(current_candle['supertrend_value']):
            self.logger.error("Invalid SuperTrend data - NaN values detected")
            return
        
        if pd.isna(previous_candle['trend_direction']) or pd.isna(previous_candle['supertrend_value']):
            self.logger.error("Invalid previous SuperTrend data - NaN values detected")
            return
        
        current_trend = int(current_candle['trend_direction'])
        previous_trend = int(previous_candle['trend_direction'])
        current_price = float(current_candle['close'])
        supertrend_value = float(current_candle['supertrend_value'])
        
        # Validate trend direction values
        if current_trend not in [-1, 1] or previous_trend not in [-1, 1]:
            self.logger.error(f"Invalid trend direction values: current={current_trend}, previous={previous_trend}")
            return
        
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
                    if balance is None or balance <= 0:
                        self.logger.warning(f"Wallet balance is None or <= 0, using default capital: {self.default_capital}")
                        balance = self.default_capital
                    
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
                if balance is None or balance <= 0:
                    self.logger.warning(f"Wallet balance is None or <= 0, using default capital: {self.default_capital}")
                    balance = self.default_capital
                
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
            url = f"{BASE_URL}/v2/history/candles" # Use BASE_URL for health check
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
    parser = argparse.ArgumentParser(description="Delta Exchange SuperTrend Trading Bot")
    parser.add_argument("--user-id", help="User ID for logging purposes")
    parser.add_argument("--strategy-name", default="supertrend", help="Name of the strategy (default: supertrend)")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode (skip initial candle wait)")
    
    args = parser.parse_args()
    
    # Get user_id from command line or environment
    user_id = args.user_id or os.environ.get('USER_ID')
    strategy_name = args.strategy_name or os.environ.get('STRATEGY_NAME', 'supertrend')
    
    print(f"Starting SuperTrend strategy for user {user_id}, strategy: {strategy_name}")
    
    try:
        bot = DeltaExchangeBot(user_id=user_id, strategy_name=strategy_name)
        
        # Log server status and health check
        bot.log_server_status()
        
        # Start the bot
        if args.test_mode:
            # In test mode, run one iteration immediately without waiting
            bot.logger.info("Running in test mode - executing one iteration immediately")
            bot.run_iteration()
            bot.logger.info("Test mode completed successfully")
        else:
            # Normal mode - start the bot with candle waiting
            bot.run()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
