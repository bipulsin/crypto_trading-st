# Configuration file for Trade Manthan Strategy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = os.getenv('BASE_URL', 'https://api.delta.exchange')
LIVE_BASE_URL = os.getenv('LIVE_BASE_URL', 'https://api.delta.exchange')
API_KEY = os.getenv('API_KEY', '')
API_SECRET = os.getenv('API_SECRET', '')

# Live API Configuration (for fallback)
LIVE_API_KEY = os.getenv('LIVE_API_KEY', '')
LIVE_API_SECRET = os.getenv('LIVE_API_SECRET', '')
LIVE_SYMBOL_ID = os.getenv('LIVE_SYMBOL_ID', '27')

# Trading Configuration
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
SYMBOL_ID = os.getenv('SYMBOL_ID', '1')
ASSET_ID = os.getenv('ASSET_ID', '3')  # Asset ID for balance checking
LEVERAGE = int(os.getenv('LEVERAGE', '1'))
ST_WITH_TRAILING = os.getenv('ST_WITH_TRAILING', 'false').lower() == 'true'

# Strategy Configuration
ST_PERIOD = int(os.getenv('ST_PERIOD', '10'))
ST_MULTIPLIER = float(os.getenv('ST_MULTIPLIER', '3.0'))
TAKE_PROFIT_MULTIPLIER = float(os.getenv('TAKE_PROFIT_MULTIPLIER', '1.5'))
POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PCT', '0.5'))
CANDLE_SIZE = os.getenv('CANDLE_SIZE', '15m')  # Default to 15 minutes

# Timing Configuration
CANDLE_INTERVAL = int(os.getenv('CANDLE_INTERVAL', '15'))  # Candle interval in minutes (5, 15, 30)
MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '30'))  # Monitoring interval in seconds

# Update CANDLE_SIZE to match CANDLE_INTERVAL
CANDLE_SIZE = f"{CANDLE_INTERVAL}m"

# SuperTrend Configuration (for backward compatibility)
SUPERTREND_PERIOD = ST_PERIOD
SUPERTREND_MULTIPLIER = ST_MULTIPLIER

# Risk Management
MAX_CAPITAL_LOSS = float(os.getenv('MAX_CAPITAL_LOSS', '0.1'))  # 10%
DEFAULT_CAPITAL = float(os.getenv('DEFAULT_CAPITAL', '1000.0'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
LOG_TO_DATABASE = os.getenv('LOG_TO_DATABASE', 'true').lower() == 'true'

# Strategy Execution Configuration
ENABLE_CONTINUOUS_MONITORING = os.getenv('ENABLE_CONTINUOUS_MONITORING', 'true').lower() == 'true'
ENABLE_CANDLE_CLOSE_ENTRIES = os.getenv('ENABLE_CANDLE_CLOSE_ENTRIES', 'true').lower() == 'true'
MAX_CLOSE_RETRIES = int(os.getenv('MAX_CLOSE_RETRIES', '3'))
RETRY_WAIT_TIME = int(os.getenv('RETRY_WAIT_TIME', '5'))
POSITION_VERIFICATION_DELAY = int(os.getenv('POSITION_VERIFICATION_DELAY', '2'))
ENABLE_CANDLE_CLOSE_AFTER_POSITION_CLOSURE = os.getenv('ENABLE_CANDLE_CLOSE_AFTER_POSITION_CLOSURE', 'true').lower() == 'true'
ENABLE_FLEXIBLE_ENTRY = os.getenv('ENABLE_FLEXIBLE_ENTRY', 'false').lower() == 'true'

# Order Management Configuration
ORDER_PRICE_OFFSET = float(os.getenv('ORDER_PRICE_OFFSET', '0.001'))  # 0.1% offset
PENDING_ORDER_MAX_ITERATIONS = int(os.getenv('PENDING_ORDER_MAX_ITERATIONS', '3'))
CANCELLATION_VERIFICATION_ENABLED = os.getenv('CANCELLATION_VERIFICATION_ENABLED', 'true').lower() == 'true'
CANCELLATION_VERIFICATION_ATTEMPTS = int(os.getenv('CANCELLATION_VERIFICATION_ATTEMPTS', '3'))
CANCELLATION_WAIT_TIME = int(os.getenv('CANCELLATION_WAIT_TIME', '2'))
VERIFICATION_WAIT_TIME = int(os.getenv('VERIFICATION_WAIT_TIME', '1'))
IMMEDIATE_REENTRY_DELAY = int(os.getenv('IMMEDIATE_REENTRY_DELAY', '5'))

# Candle Close Buffer Configuration
CANDLE_CLOSE_BUFFER = int(os.getenv('CANDLE_CLOSE_BUFFER', '10'))  # Seconds before candle close

# Validation Configuration
VALIDATE_EXISTING_ORDERS = os.getenv('VALIDATE_EXISTING_ORDERS', 'true').lower() == 'true'
MAX_CAPITAL_LOSS_PERCENT = float(os.getenv('MAX_CAPITAL_LOSS_PERCENT', '5.0'))  # 5% max loss

# Additional Configuration Variables
CANDLE_FALLBACK_ENABLED = os.getenv('CANDLE_FALLBACK_ENABLED', 'true').lower() == 'true'
ENABLE_IMMEDIATE_REENTRY = os.getenv('ENABLE_IMMEDIATE_REENTRY', 'false').lower() == 'true'
MAX_ITERATION_TIME = int(os.getenv('MAX_ITERATION_TIME', '60'))  # Maximum iteration time in seconds
