#!/usr/bin/env python3

def fix_wallet_balance_handling():
    """Fix the get_wallet_balance method to handle API errors gracefully"""
    
    # Read the current file
    with open('strategy_st.py', 'r') as f:
        content = f.read()
    
    # Find and replace the get_wallet_balance method
    old_method = '''    def get_wallet_balance(self) -> float:
        """Get wallet balance using delta_api"""
        return self.api.get_wallet_balance()'''
    
    new_method = '''    def get_wallet_balance(self) -> float:
        """Get wallet balance using delta_api with error handling"""
        try:
            balance = self.api.get_wallet_balance()
            if balance is not None and balance > 0:
                return balance
            else:
                self.logger.warning("Wallet balance is None or <= 0, using default capital")
                return self.default_capital
        except Exception as e:
            self.logger.error(f"Failed to get wallet balance: {e}")
            self.logger.warning("Using default capital due to API error")
            return self.default_capital'''
    
    # Replace the method
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Successfully updated get_wallet_balance method")
    else:
        print("❌ Could not find the old method to replace")
        return False
    
    # Also add a default_capital attribute to the __init__ method
    old_init = '''        self.take_profit_multiplier = float(os.getenv('STRATEGY_TAKE_PROFIT_MULTIPLIER', '1.5'))
        self.trailing_stop = os.getenv('STRATEGY_TRAILING_STOP', 'false').lower() == 'true'
        
        # Initialize SuperTrend calculation'''
    
    new_init = '''        self.take_profit_multiplier = float(os.getenv('STRATEGY_TAKE_PROFIT_MULTIPLIER', '1.5'))
        self.trailing_stop = os.getenv('STRATEGY_TRAILING_STOP', 'false').lower() == 'true'
        self.default_capital = float(os.getenv('DEFAULT_CAPITAL', '1000.0'))
        
        # Initialize SuperTrend calculation'''
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ Successfully added default_capital attribute")
    else:
        print("❌ Could not find the init method to update")
        return False
    
    # Write the updated content back
    with open('strategy_st.py', 'w') as f:
        f.write(content)
    
    print("✅ File updated successfully")
    return True

if __name__ == "__main__":
    fix_wallet_balance_handling()
