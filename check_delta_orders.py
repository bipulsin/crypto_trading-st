import requests
from logger import get_logger

# Set up logger
logger = get_logger('check_delta_orders', 'logs/check_delta_orders.log')

def check_orders():
    """Check current orders on Delta exchange"""
    try:
        url = "https://api.delta.exchange/v2/orders"
        response = requests.get(url)
        
        logger.info("Status code:", response.status_code)
        logger.info("Response:", response.text)
        
        return response.json()
    except Exception as e:
        logger.error("Error:", e)
        return None

if __name__ == "__main__":
    check_orders() 