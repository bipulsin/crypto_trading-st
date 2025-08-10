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
CANDLE_SIZE = os.getenv('CANDLE_SIZE', '5m')

# Risk Management
MAX_CAPITAL_LOSS = float(os.getenv('MAX_CAPITAL_LOSS', '0.1'))  # 10%
DEFAULT_CAPITAL = float(os.getenv('DEFAULT_CAPITAL', '1000.0'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
LOG_TO_DATABASE = os.getenv('LOG_TO_DATABASE', 'true').lower() == 'true'
