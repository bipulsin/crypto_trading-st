#!/usr/bin/env python3

import re

def fix_strategy_timing():
    """Fix the wait_for_next_candle method to use STRATEGY_CANDLE_SIZE instead of hardcoded 5 minutes"""
    
    # Read the current file
    with open('strategy_st.py', 'r') as f:
        content = f.read()
    
    # Find and replace the wait_for_next_candle method
    old_method = '''    def wait_for_next_candle(self):
        """Wait for next 5-minute candle"""
        now = datetime.now()
        next_candle = now.replace(second=0, microsecond=0)
        
        # Round to next 5-minute interval
        minutes = (next_candle.minute // 5 + 1) * 5
        if minutes >= 60:
            # Use timedelta to safely handle hour overflow
            next_candle = next_candle.replace(minute=0) + timedelta(hours=1)
        else:
            next_candle = next_candle.replace(minute=minutes)
        
        wait_seconds = (next_candle - now).total_seconds()
        
        if wait_seconds > 0:
            self.logger.info(f"Waiting {wait_seconds:.1f} seconds for next candle at {next_candle}")
            time.sleep(wait_seconds)'''
    
    new_method = '''    def wait_for_next_candle(self):
        """Wait for next candle based on configured STRATEGY_CANDLE_SIZE"""
        now = datetime.now()
        next_candle = now.replace(second=0, microsecond=0)
        
        # Parse the candle size to get minutes
        candle_minutes = 5  # Default to 5 minutes
        if self.resolution.endswith("m"):
            try:
                candle_minutes = int(self.resolution[:-1])
            except ValueError:
                candle_minutes = 5
        elif self.resolution.endswith("h"):
            try:
                candle_minutes = int(self.resolution[:-1]) * 60
            except ValueError:
                candle_minutes = 60
        
        # Round to next candle interval
        minutes = (next_candle.minute // candle_minutes + 1) * candle_minutes
        if minutes >= 60:
            # Use timedelta to safely handle hour overflow
            next_candle = next_candle.replace(minute=0) + timedelta(hours=1)
        else:
            next_candle = next_candle.replace(minute=minutes)
        
        wait_seconds = (next_candle - now).total_seconds()
        
        if wait_seconds > 0:
            self.logger.info(f"Waiting {wait_seconds:.1f} seconds for next {self.resolution} candle at {next_candle}")
            time.sleep(wait_seconds)'''
    
    # Replace the method
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Successfully updated wait_for_next_candle method")
    else:
        print("❌ Could not find the old method to replace")
        return False
    
    # Write the updated content back
    with open('strategy_st.py', 'w') as f:
        f.write(content)
    
    print("✅ File updated successfully")
    return True

if __name__ == "__main__":
    fix_strategy_timing()
