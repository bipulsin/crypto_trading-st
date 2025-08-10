#!/usr/bin/env python3
"""
Configure Broker Connection from Database on EC2
"""

import sqlite3
import os
import json
from dotenv import load_dotenv

def get_broker_connection_from_db():
    """Get broker connection details from database"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Get the most recent broker connection
        cursor.execute("""
            SELECT api_key, api_secret, broker_url 
            FROM broker_connections 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            api_key, api_secret, broker_url = result
            return {
                'api_key': api_key,
                'api_secret': api_secret,
                'broker_url': broker_url
            }
        else:
            print("❌ No broker connection found in database")
            return None
            
    except Exception as e:
        print(f"❌ Error reading broker connection from database: {e}")
        return None

def get_strategy_config_from_db():
    """Get strategy configuration from database"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Get the most recent strategy config
        cursor.execute("""
            SELECT config_data, symbol, symbol_id 
            FROM strategy_configs 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            config_data, symbol, symbol_id = result
            config = json.loads(config_data)
            return {
                'symbol': symbol,
                'symbol_id': symbol_id,
                'config': config
            }
        else:
            print("❌ No strategy config found in database")
            return None
            
    except Exception as e:
        print(f"❌ Error reading strategy config from database: {e}")
        return None

def update_env_file(broker_config, strategy_config):
    """Update .env file with broker connection and strategy config"""
    try:
        # Read current .env file
        env_content = ""
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                env_content = f.read()
        
        # Parse existing content
        env_vars = {}
        for line in env_content.split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        
        # Update with broker connection
        if broker_config:
            env_vars['API_KEY'] = broker_config['api_key']
            env_vars['API_SECRET'] = broker_config['api_secret']
            env_vars['BASE_URL'] = broker_config['broker_url']
            print(f"✅ Updated broker connection: {broker_config['broker_url']}")
        
        # Update with strategy config
        if strategy_config:
            config = strategy_config['config']
            env_vars['SYMBOL'] = strategy_config['symbol']
            env_vars['SYMBOL_ID'] = strategy_config['symbol_id']
            env_vars['ST_PERIOD'] = str(config.get('st_period', 10))
            env_vars['ST_MULTIPLIER'] = str(config.get('st_multiplier', 3.0))
            env_vars['TAKE_PROFIT_MULTIPLIER'] = str(config.get('take_profit_multiplier', 1.5))
            env_vars['POSITION_SIZE_PCT'] = str(config.get('position_size_pct', 0.5))
            env_vars['LEVERAGE'] = str(config.get('leverage', 1))
            env_vars['STRATEGY_CANDLE_SIZE'] = config.get('candle_size', '5m')
            print(f"✅ Updated strategy config: {strategy_config['symbol']} (ID: {strategy_config['symbol_id']})")
        
        # Add default values for missing variables
        defaults = {
            'DEFAULT_CAPITAL': '1000.0',
            'STRATEGY_TRAILING_STOP': 'false',
            'ST_WITH_TRAILING': 'false'
        }
        
        for key, value in defaults.items():
            if key not in env_vars:
                env_vars[key] = value
        
        # Write updated .env file
        with open('.env', 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        print("✅ .env file updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def main():
    """Main function to configure broker connection"""
    print("🔧 Configuring Broker Connection from Database...")
    
    # Get broker connection from database
    broker_config = get_broker_connection_from_db()
    if not broker_config:
        print("❌ Failed to get broker connection from database")
        return False
    
    # Get strategy config from database
    strategy_config = get_strategy_config_from_db()
    if not strategy_config:
        print("❌ Failed to get strategy config from database")
        return False
    
    # Check if API credentials are valid (not empty or placeholder)
    if (broker_config['api_key'] in ['YOUR_API_KEY_HERE', '', None] or 
        broker_config['api_secret'] in ['YOUR_API_SECRET_HERE', '', None]):
        print("⚠️  WARNING: API credentials are placeholder values or empty!")
        print("   Please update the broker_connections table with real API credentials")
        print("   You can do this by:")
        print("   1. SSH into EC2: ssh -i trademanthan.pem ubuntu@13.115.183.85")
        print("   2. Navigate to: cd deploy_package")
        print("   3. Update credentials: sqlite3 users.db \"UPDATE broker_connections SET api_key='YOUR_REAL_API_KEY', api_secret='YOUR_REAL_API_SECRET' WHERE id=1;\"")
        return False
    
    # Update .env file
    if update_env_file(broker_config, strategy_config):
        print("\n🎯 Configuration Summary:")
        print(f"   Broker URL: {broker_config['broker_url']}")
        print(f"   Symbol: {strategy_config['symbol']} (ID: {strategy_config['symbol_id']})")
        print(f"   SuperTrend Period: {strategy_config['config'].get('st_period', 10)}")
        print(f"   SuperTrend Multiplier: {strategy_config['config'].get('st_multiplier', 3.0)}")
        print(f"   Take Profit Multiplier: {strategy_config['config'].get('take_profit_multiplier', 1.5)}")
        print(f"   Position Size: {strategy_config['config'].get('position_size_pct', 0.5) * 100}%")
        print(f"   Leverage: {strategy_config['config'].get('leverage', 1)}x")
        print(f"   Candle Size: {strategy_config['config'].get('candle_size', '5m')}")
        
        print("\n✅ Broker connection configured successfully!")
        print("   You can now restart the strategy with: python3 strategy_st.py")
        return True
    else:
        print("❌ Failed to configure broker connection")
        return False

if __name__ == "__main__":
    main()
