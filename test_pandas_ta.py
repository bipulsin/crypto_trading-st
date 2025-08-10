#!/usr/bin/env python3

import warnings
import sys

# Suppress all warnings
warnings.filterwarnings("ignore")

print("=== TESTING PANDAS_TA ===")

try:
    import pandas as pd
    print("✓ pandas imported successfully")
    
    import pandas_ta as ta
    print("✓ pandas_ta imported successfully")
    
    # Test SuperTrend calculation
    print("Testing SuperTrend calculation...")
    
    # Create sample data
    data = {
        'high': [100, 101, 102, 103, 104],
        'low': [99, 100, 101, 102, 103],
        'close': [100.5, 100.8, 101.2, 102.5, 103.8]
    }
    df = pd.DataFrame(data)
    
    print(f"Sample data: {df}")
    
    # Calculate SuperTrend
    st = ta.supertrend(df['high'], df['low'], df['close'], length=3, multiplier=2)
    print(f"SuperTrend result: {st}")
    
    print("✓ SuperTrend calculation successful")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=== TEST COMPLETED SUCCESSFULLY ===")
