#!/usr/bin/env python3
import os
import sys
import time
import argparse

def main():
    """Test strategy script that just logs environment and exits"""
    parser = argparse.ArgumentParser(description="Test Strategy Script")
    parser.add_argument("--user-id", help="User ID for logging purposes")
    parser.add_argument("--strategy-name", default="test", help="Name of the strategy")
    
    args = parser.parse_args()
    
    print("=== TEST STRATEGY STARTED ===")
    print(f"User ID: {args.user_id}")
    print(f"Strategy Name: {args.strategy_name}")
    print(f"Environment USER_ID: {os.getenv('USER_ID')}")
    print(f"Environment BASE_URL: {os.getenv('BASE_URL')}")
    print(f"Environment API_KEY: {os.getenv('API_KEY', 'Not set')[:10] if os.getenv('API_KEY') else 'Not set'}")
    print(f"Environment STRATEGY_CANDLE_SIZE: {os.getenv('STRATEGY_CANDLE_SIZE')}")
    print(f"Environment STRATEGY_TRAILING_STOP: {os.getenv('STRATEGY_TRAILING_STOP')}")
    print("=== TEST STRATEGY COMPLETED ===")
    
    # Simulate some work
    time.sleep(1)
    print("Strategy test completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()
