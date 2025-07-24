import requests
import os

# You can set your API key and secret here or use environment variables
API_KEY = os.getenv('DELTA_API_KEY_TEST', 'YOUR_API_KEY')
API_SECRET = os.getenv('DELTA_API_SECRET_TEST', 'YOUR_API_SECRET')
BASE_URL = 'https://cdn-ind.testnet.deltaex.org'

url = f"{BASE_URL}/v2/orders"
headers = {
    'Content-Type': 'application/json',
    # Add authentication headers if required by the API
    # 'api-key': API_KEY,
    # 'api-signature': '...',
    # 'api-request-expiry': '...',
}

try:
    response = requests.get(url, headers=headers)
    print("Status code:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e) 