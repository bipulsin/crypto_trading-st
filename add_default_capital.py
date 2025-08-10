#!/usr/bin/env python3

import os

def add_default_capital():
    """Add default_capital attribute to the __init__ method"""
    
    # Read the current file
    with open('strategy_st.py', 'r') as f:
        content = f.read()
    
    # Find the line with trailing stop configuration and add default_capital after it
    old_line = '''        # Trailing Stop Loss Configuration
        self.st_with_trailing = STRATEGY_TRAILING_STOP # Use strategy-specific trailing stop
        self.trailing_stop_distance = 100  # 100 points trailing distance (fallback)'''
    
    new_line = '''        # Trailing Stop Loss Configuration
        self.st_with_trailing = STRATEGY_TRAILING_STOP # Use strategy-specific trailing stop
        self.trailing_stop_distance = 100  # 100 points trailing distance (fallback)
        
        # Default capital for fallback when API fails
        self.default_capital = float(os.environ.get('DEFAULT_CAPITAL', '1000.0'))'''
    
    # Replace the lines
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("✅ Successfully added default_capital attribute")
    else:
        print("❌ Could not find the trailing stop configuration to update")
        return False
    
    # Write the updated content back
    with open('strategy_st.py', 'w') as f:
        f.write(content)
    
    print("✅ File updated successfully")
    return True

if __name__ == "__main__":
    add_default_capital()
