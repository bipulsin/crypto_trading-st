import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TRADING_FROM_LIVE = False

# Live market data API parameters (for non-order related calls)
LIVE_BASE_URL = 'https://api.india.delta.exchange' 
LIVE_API_KEY = 'Fp0bn5wr4qZ1A1AHz17NdVf8Pxp8Ct' 
LIVE_API_SECRET = 'SAsjx9iewya4yvLO5e3L7uKwVNOBQ7ernVhkMOU6BUaErxWNFLmE8m8ZLIiq'  
LIVE_SYMBOL_ID = 27 

if TRADING_FROM_LIVE:
    BASE_URL = LIVE_BASE_URL
    API_KEY = LIVE_API_KEY
    API_SECRET = LIVE_API_SECRET
    SYMBOL_ID = LIVE_SYMBOL_ID
else:
    BASE_URL = 'https://cdn-ind.testnet.deltaex.org'
    API_KEY = os.getenv('DELTA_API_KEY_TEST', 'Dif1lSZl16ibEVhqKboD1UkQ5Z4qD7')
    API_SECRET = os.getenv('DELTA_API_SECRET_TEST', 'kjDLM1vF5GI8THQylfIBRyMmfrL3pkheUomTBmJLCVJHwVCz0Fuk5KCA5WYH')
    SYMBOL_ID = 84

SYMBOL = 'BTCUSD'


CAPITAL_MODE = '100%'
CANDLE_INTERVAL = 5
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3
ASSET_ID = 3


# Order management configuration
RESPECT_EXISTING_ORDERS = True  # Set to False to cancel existing orders on startup
AUTO_CANCEL_OLD_ORDERS = False  # Set to True to automatically cancel orders older than specified hours
MAX_ORDER_AGE_HOURS = 24  # Maximum age of orders to keep (if AUTO_CANCEL_OLD_ORDERS is True)

# Risk management configuration
MAX_CAPITAL_LOSS_PERCENT = 30  # Maximum loss percentage before closing existing orders
VALIDATE_EXISTING_ORDERS = True  # Validate existing orders against SuperTrend and risk rules
AUTO_CLOSE_INVALID_ORDERS = True  # Automatically close orders that violate trading rules

# Trading configuration
DEFAULT_CAPITAL = 200  # Default capital if balance cannot be retrieved
LEVERAGE = 50  # Leverage used for position sizing
POSITION_SIZE_PERCENT = 0.5  # Percentage of balance to use for each trade
TAKE_PROFIT_MULTIPLIER = 1.25  # Multiplier for take profit calculation
ORDER_PRICE_OFFSET = 10  # Price offset for limit orders ($100 above/below market)

# Performance and monitoring
MAX_ITERATION_TIME = 2.0  # Maximum acceptable iteration time in seconds
PENDING_ORDER_MAX_ITERATIONS = 2  # Maximum iterations to wait for pending orders
CANDLE_FALLBACK_ENABLED = True  # Enable Binance fallback for candle data

# Order cancellation settings
CANCELLATION_VERIFICATION_ENABLED = True  # Enable verification after cancellation
CANCELLATION_VERIFICATION_ATTEMPTS = 2  # Number of verification attempts
CANCELLATION_WAIT_TIME = 3  # Seconds to wait between cancellation attempts
VERIFICATION_WAIT_TIME = 2  # Seconds to wait between verification attempts

# Enhanced error handling and retry settings
MAX_CANCEL_RETRIES = 3  # Maximum retries for order cancellation
MAX_CLOSE_RETRIES = 3  # Maximum retries for position closing
RETRY_WAIT_TIME = 2  # Seconds to wait between retries
ORDER_VERIFICATION_TIMEOUT = 10  # Timeout for order verification operations
POSITION_VERIFICATION_DELAY = 2  # Seconds to wait before verifying position closure

# Performance monitoring thresholds
MAX_ORDER_PLACEMENT_TIME = 2.0  # Maximum acceptable order placement time (seconds)
MAX_TOTAL_EXECUTION_TIME = 5.0  # Maximum acceptable total trade execution time (seconds)
PERFORMANCE_WARNING_THRESHOLD = 2.0  # Warning threshold for execution time (seconds)

# Trading timing and execution logic
ENABLE_CONTINUOUS_MONITORING = True  # Enable continuous position/order monitoring
ENABLE_CANDLE_CLOSE_ENTRIES = True  # Only place new orders at candle close
MONITORING_INTERVAL = 60  # Seconds between monitoring checks (when not at candle close)
CANDLE_CLOSE_BUFFER = 10  # Seconds buffer before candle close to prepare for entry

# New: Immediate order placement after cancellation
ENABLE_IMMEDIATE_REENTRY = True  # Allow immediate new order placement after cancellation
IMMEDIATE_REENTRY_DELAY = 5  # Seconds to wait before placing new order after cancellation
ENABLE_FLEXIBLE_ENTRY = False  # Allow new orders anytime (not just at candle close)
