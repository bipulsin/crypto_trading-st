#!/usr/bin/env python3
"""
Setup EC2 Database with Broker Connection Configuration
"""

import sqlite3
import json

def setup_ec2_database():
    """Set up the database on EC2 with broker connection configuration"""
    
    # Connect to database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        # Create default user
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, name, email) 
            VALUES (?, ?, ?)
        """, ("default_user", "Default User", "default@example.com"))
        
        # Create broker connection for Delta Exchange
        cursor.execute("""
            INSERT OR IGNORE INTO broker_connections 
            (user_id, connection_name, broker_id, broker_url, api_key, api_secret) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "default_user", 
            "Delta Exchange Testnet", 
            "delta_exchange", 
            "https://api.delta.exchange", 
            "YOUR_API_KEY_HERE", 
            "YOUR_API_SECRET_HERE"
        ))
        
        # Create user settings
        cursor.execute("""
            INSERT OR IGNORE INTO user_settings 
            (user_id, leverage, position_size_percent, default_capital, max_capital_loss_percent, broker_connection_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("default_user", 1.0, 0.5, 1000.0, 0.1, 1))
        
        # Create strategy configuration
        config_data = {
            "st_period": 10,
            "st_multiplier": 3.0,
            "take_profit_multiplier": 1.5,
            "position_size_pct": 0.5,
            "leverage": 1,
            "candle_size": "5m"
        }
        
        cursor.execute("""
            INSERT OR IGNORE INTO strategy_configs 
            (user_id, strategy_name, broker_connection_id, symbol, symbol_id, config_data, is_active) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "default_user", 
            "supertrend", 
            1, 
            "BTCUSD", 
            "84", 
            json.dumps(config_data), 
            1
        ))
        
        # Commit changes
        conn.commit()
        print("✅ Database setup completed successfully!")
        
        # Show what was created
        print("\n📊 Database Contents:")
        
        print("\n👥 Users:")
        cursor.execute("SELECT * FROM users")
        for row in cursor.fetchall():
            print(f"  - {row}")
        
        print("\n🔗 Broker Connections:")
        cursor.execute("SELECT * FROM broker_connections")
        for row in cursor.fetchall():
            print(f"  - {row}")
        
        print("\n⚙️  User Settings:")
        cursor.execute("SELECT * FROM user_settings")
        for row in cursor.fetchall():
            print(f"  - {row}")
        
        print("\n📈 Strategy Configs:")
        cursor.execute("SELECT * FROM strategy_configs")
        for row in cursor.fetchall():
            print(f"  - {row}")
            
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    setup_ec2_database()
