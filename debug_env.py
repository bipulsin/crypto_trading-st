#!/usr/bin/env python3
import os
import sys

print("=== DEBUG ENVIRONMENT VARIABLES ===")
print(f"USER_ID: {os.getenv('USER_ID', 'Not set')}")
print(f"STRATEGY_NAME: {os.getenv('STRATEGY_NAME', 'Not set')}")
print(f"BASE_URL: {os.getenv('BASE_URL', 'Not set')}")
print(f"API_KEY: {os.getenv('API_KEY', 'Not set')}")
print(f"API_SECRET: {os.getenv('API_SECRET', 'Not set')}")
print(f"BROKER_CONNECTION_ID: {os.getenv('BROKER_CONNECTION_ID', 'Not set')}")
print(f"CONNECTION_NAME: {os.getenv('CONNECTION_NAME', 'Not set')}")
print(f"STRATEGY_TAKE_PROFIT_MULTIPLIER: {os.getenv('STRATEGY_TAKE_PROFIT_MULTIPLIER', 'Not set')}")
print(f"STRATEGY_TRAILING_STOP: {os.getenv('STRATEGY_TRAILING_STOP', 'Not set')}")
print(f"STRATEGY_CANDLE_SIZE: {os.getenv('STRATEGY_CANDLE_SIZE', 'Not set')}")
print("==================================")

# Check if we can import required modules
try:
    import pandas as pd
    print("✓ pandas imported successfully")
except ImportError as e:
    print(f"✗ pandas import failed: {e}")

try:
    import pandas_ta as ta
    print("✓ pandas_ta imported successfully")
except ImportError as e:
    print(f"✗ pandas_ta import failed: {e}")

try:
    from delta_api import DeltaAPI
    print("✓ delta_api imported successfully")
except ImportError as e:
    print(f"✗ delta_api import failed: {e}")

print("=== DEBUG COMPLETED ===")
