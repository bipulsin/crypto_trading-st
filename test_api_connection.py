#!/usr/bin/env python3
"""
Test Delta Exchange API Connection
"""
import os
import time
import hashlib
import hmac
import json
import requests
from dotenv import load_dotenv

def test_delta_api_connection():
    """Test Delta Exchange API connection with current credentials"""
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    base_url = os.getenv('BASE_URL', 'https://api.delta.exchange')
    
    print(f"🔑 Testing Delta Exchange API Connection")
    print(f"   Base URL: {base_url}")
    print(f"   API Key: {api_key[:10]}..." if api_key else "   API Key: NOT SET")
    print(f"   API Secret: {api_secret[:10]}..." if api_secret else "   API Secret: NOT SET")
    print()
    
    if not api_key or not api_secret:
        print("❌ API credentials not set")
        return False
    
    # Test 1: Simple GET request to public endpoint
    print("📡 Test 1: Public endpoint (no authentication)")
    try:
        response = requests.get(f"{base_url}/v2/products", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: Found {len(data.get('result', []))} products")
        else:
            print(f"   ❌ Failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 2: Authenticated request to wallet balances
    print("📡 Test 2: Authenticated endpoint (wallet balances)")
    
    # Generate signature
    timestamp = str(int(time.time()))
    path = "/v2/wallet/balances"
    message = "GET" + timestamp + path + ""
    signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }
    
    print(f"   Timestamp: {timestamp}")
    print(f"   Message: {message}")
    print(f"   Signature: {signature[:20]}...")
    print()
    
    try:
        url = f"{base_url}{path}"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                balances = data.get('result', [])
                print(f"   ✅ Success: Found {len(balances)} balance entries")
                for balance in balances[:3]:  # Show first 3
                    currency = balance.get('asset_symbol', 'Unknown')
                    available = balance.get('available_balance', 0)
                    print(f"      {currency}: {available}")
            else:
                print(f"   ❌ API Error: {data}")
        elif response.status_code == 401:
            print("   ❌ 401 Unauthorized - Check API credentials and permissions")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 3: Check if testnet URL works
    print("📡 Test 3: Testnet endpoint")
    testnet_url = "https://testnet-api.delta.exchange"
    
    try:
        response = requests.get(f"{testnet_url}/v2/products", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Testnet accessible")
        else:
            print(f"   ❌ Testnet not accessible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Testnet error: {e}")
    
    print()
    print("🎯 API Connection Test Complete")

if __name__ == "__main__":
    test_delta_api_connection()
