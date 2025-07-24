import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print('python-dotenv not installed; environment variables from .env will not be loaded.')


# Delta Exchange API base URL - LIVE
# BASE_URL = 'https://api.india.delta.exchange'
# Delta Exchange API base URL - TEST
BASE_URL = 'https://cdn-ind.testnet.deltaex.org'


# Delta Exchange API credentials - LIVE
# API_KEY = os.getenv('DELTA_API_KEY', 'B9t89bOwYNEv3faToie0Q2FSPQGVXV')
#API_SECRET = os.getenv('DELTA_API_SECRET', 'SeE9hkDsbRHLFnsTT0L2MW6FXoIELhtqSEY3no6fI7P3VCD16qs4ACL27wIJ')

# Delta Exchange API credentials - TEST
API_KEY = os.getenv('DELTA_API_KEY_TEST', 'Dif1lSZl16ibEVhqKboD1UkQ5Z4qD7')
API_SECRET = os.getenv('DELTA_API_SECRET_TEST', 'kjDLM1vF5GI8THQylfIBRyMmfrL3pkheUomTBmJLCVJHwVCz0Fuk5KCA5WYH')

# Trading parameters
SYMBOL = 'BTCUSD'
SYMBOL_ID = 84  # Updated to match testnet product ID for LIVE use 27
CAPITAL_MODE = '100%'  # Use 100% of available capital
CANDLE_INTERVAL = 5  # minutes
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3
ASSET_ID = 3



# Email notification settings (Gmail SMTP)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USER = os.getenv('EMAIL_USER', 'webnetin@gmail.com')
EMAIL_PASS = os.getenv('EMAIL_PASS', 'Bs2670!@')
EMAIL_TO = os.getenv('EMAIL_TO', 'webnetin@gmail.com')
