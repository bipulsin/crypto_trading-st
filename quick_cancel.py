#!/usr/bin/env python3
"""
Quick order cancellation utility
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from delta_api import DeltaAPI
from config import SYMBOL_ID

def quick_cancel_orders(product_id=None):
    """
    Quick cancel all orders for a product ID
    
    Args:
        product_id (int): Product ID to cancel orders for. If None, uses SYMBOL_ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    if product_id is None:
        product_id = SYMBOL_ID
    
    try:
        api = DeltaAPI()
        
        # Try the new CancelAllFilterObject API first
        result = api.cancel_all_orders_by_product(product_id)
        if result.get('success'):
            print(f"✅ Successfully cancelled orders for product ID {product_id}")
            return True
        
        # Fallback to legacy method
        success = api.cancel_all_orders()
        if success:
            print(f"✅ Successfully cancelled orders for product ID {product_id} (legacy method)")
            return True
        
        print(f"❌ Failed to cancel orders for product ID {product_id}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            product_id = int(sys.argv[1])
            quick_cancel_orders(product_id)
        except ValueError:
            print(f"❌ Invalid product ID: {sys.argv[1]}")
    else:
        quick_cancel_orders() 