#!/usr/bin/env python3
"""
Debug Broker Connection Reading
"""

import sqlite3
import json

def debug_broker_connection():
    """Debug what's being read from the database"""
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        print("🔍 Debugging Broker Connection Reading...")
        print("=" * 50)
        
        # Get the most recent broker connection
        cursor.execute("""
            SELECT api_key, api_secret, broker_url 
            FROM broker_connections 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            api_key, api_secret, broker_url = result
            print(f"📊 Raw database result: {result}")
            print(f"🔑 API Key: '{api_key}' (type: {type(api_key)}, length: {len(api_key) if api_key else 0})")
            print(f"🔐 API Secret: '{api_secret}' (type: {type(api_secret)}, length: {len(api_secret) if api_secret else 0})")
            print(f"🌐 Broker URL: '{broker_url}'")
            
            # Test the validation logic
            placeholder_check = (
                api_key in ['YOUR_API_KEY_HERE', '', None] or 
                api_secret in ['YOUR_API_SECRET_HERE', '', None]
            )
            
            print(f"\n🧪 Validation Test:")
            print(f"   Is placeholder: {placeholder_check}")
            print(f"   API Key in ['YOUR_API_KEY_HERE', '', None]: {api_key in ['YOUR_API_KEY_HERE', '', None]}")
            print(f"   API Secret in ['YOUR_API_SECRET_HERE', '', None]: {api_secret in ['YOUR_API_SECRET_HERE', '', None]}")
            
            if not placeholder_check:
                print("✅ Credentials appear valid!")
            else:
                print("❌ Credentials appear to be placeholders")
                
        else:
            print("❌ No broker connection found in database")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_broker_connection()
