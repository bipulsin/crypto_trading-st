#!/usr/bin/env python3
"""
Quick order cancellation utility
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from delta_api import DeltaAPI
from config import SYMBOL_ID
from logger import get_logger

# Set up logger
logger = get_logger('quick_cancel', 'logs/quick_cancel.log')

def cancel_orders_for_product(product_id):
    """Cancel all orders for a specific product ID"""
    try:
        api = DeltaAPI()
        
        # Try the new method first
        try:
            result = api.cancel_all_orders_by_product(product_id=product_id)
            if result:
                logger.info(f"✅ Successfully cancelled orders for product ID {product_id}")
                return True
        except Exception as e:
            logger.warning(f"New method failed, trying legacy method: {e}")
        
        # Fallback to legacy method
        try:
            result = api.cancel_all_orders()
            if result:
                logger.info(f"✅ Successfully cancelled orders for product ID {product_id} (legacy method)")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to cancel orders for product ID {product_id}")
            logger.error(f"❌ Error: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python quick_cancel.py <product_id>")
        sys.exit(1)
    
    try:
        product_id = int(sys.argv[1])
        cancel_orders_for_product(product_id)
    except ValueError:
        logger.error(f"❌ Invalid product ID: {sys.argv[1]}")
        sys.exit(1) 