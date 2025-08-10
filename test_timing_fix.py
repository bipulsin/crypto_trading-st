#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta

# Set the environment variable for testing
os.environ['STRATEGY_CANDLE_SIZE'] = '15m'

def test_timing_logic():
    """Test the timing logic with 15m candle size"""
    
    # Simulate the logic from wait_for_next_candle method
    resolution = '15m'
    
    print(f"Testing with resolution: {resolution}")
    
    # Parse the candle size to get minutes
    candle_minutes = 5  # Default to 5 minutes
    if resolution.endswith("m"):
        try:
            candle_minutes = int(resolution[:-1])
            print(f"Parsed minutes: {candle_minutes}")
        except ValueError:
            candle_minutes = 5
            print(f"Parse failed, using default: {candle_minutes}")
    elif resolution.endswith("h"):
        try:
            candle_minutes = int(resolution[:-1]) * 60
            print(f"Parsed hours to minutes: {candle_minutes}")
        except ValueError:
            candle_minutes = 60
            print(f"Parse failed, using default: {candle_minutes}")
    
    # Test with current time
    now = datetime.now()
    print(f"Current time: {now}")
    
    # Round to next candle interval
    minutes = (now.minute // candle_minutes + 1) * candle_minutes
    if minutes >= 60:
        # Use timedelta to safely handle hour overflow
        next_candle = now.replace(minute=0) + timedelta(hours=1)
    else:
        next_candle = now.replace(minute=minutes)
    
    print(f"Next candle time: {next_candle}")
    
    wait_seconds = (next_candle - now).total_seconds()
    print(f"Wait seconds: {wait_seconds:.1f}")
    
    # Convert to minutes for verification
    wait_minutes = wait_seconds / 60
    print(f"Wait minutes: {wait_minutes:.1f}")
    
    # Verify it's approximately 15 minutes or less
    if wait_minutes <= 15:
        print("✅ Timing logic working correctly - wait time is reasonable")
    else:
        print("❌ Timing logic issue - wait time too long")
    
    return wait_minutes <= 15

if __name__ == "__main__":
    success = test_timing_logic()
    sys.exit(0 if success else 1)
