import time
import pandas as pd
from delta_api import DeltaAPI
from supertrend import calculate_supertrend
from live_strategy import LiveStrategy
from config import (SYMBOL, CANDLE_INTERVAL, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER, 
                   DEFAULT_CAPITAL, MAX_ITERATION_TIME, PENDING_ORDER_MAX_ITERATIONS, 
                   CANDLE_FALLBACK_ENABLED, ORDER_PRICE_OFFSET, TAKE_PROFIT_MULTIPLIER,
                   CANCELLATION_VERIFICATION_ENABLED, CANCELLATION_VERIFICATION_ATTEMPTS,
                   CANCELLATION_WAIT_TIME, VERIFICATION_WAIT_TIME)
import datetime
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# Initialize modules
api = DeltaAPI()
strategy = LiveStrategy(api)
capital = DEFAULT_CAPITAL

# Global state tracking
prev_supertrend_signal = None
pending_order_iterations = 0
last_order_id = None

def fetch_candles_optimized():
    try:
        end_time = int(time.time())
        start_time = end_time - (100 * CANDLE_INTERVAL * 60)
        candle_data = api.get_candles(
            symbol=SYMBOL, 
            interval=f'{CANDLE_INTERVAL}m', 
            limit=100, 
            start=start_time, 
            end=end_time
        )
        candles = pd.DataFrame(candle_data)
        candles['datetime'] = pd.to_datetime(candles['time'], unit='s')
        candles = candles.sort_values('datetime')
        return candles
    except Exception as e:
        log(f"Error fetching candles: {e}")
        return None

def calculate_supertrend_optimized(candles):
    try:
        return calculate_supertrend(candles, period=SUPERTREND_PERIOD, multiplier=SUPERTREND_MULTIPLIER)
    except Exception as e:
        log(f"Error calculating SuperTrend: {e}")
        return None

def run_strategy_optimized(candles, capital):
    try:
        return strategy.decide(candles, capital)
    except Exception as e:
        log(f"Error in strategy decision: {e}")
        return None

def get_current_capital():
    """Get current capital for risk management calculations"""
    try:
        balance = api.get_balance()
        # Use the balance as capital, or you can modify this logic based on your needs
        return balance if balance > 0 else DEFAULT_CAPITAL  # Fallback to default capital
    except Exception as e:
        log(f"⚠️ Error getting current capital: {e}")
        return DEFAULT_CAPITAL  # Fallback to default capital

def validate_existing_order_against_strategy(order, current_supertrend_signal, current_mark_price, capital):
    """Validate if an existing order aligns with current SuperTrend strategy and risk rules"""
    from config import MAX_CAPITAL_LOSS_PERCENT, VALIDATE_EXISTING_ORDERS
    
    if not VALIDATE_EXISTING_ORDERS:
        return {"valid": True, "reason": "Validation disabled"}
    
    try:
        order_side = order.get('side', '').lower()
        order_size_raw = order.get('size', 0)
        order_price_raw = order.get('limit_price', 0)
        stop_loss_price_raw = order.get('bracket_stop_loss_price', 0)
        
        # Handle None values and convert to float safely
        try:
            order_size = float(order_size_raw) if order_size_raw is not None else 0
        except (ValueError, TypeError):
            order_size = 0
            
        try:
            order_price = float(order_price_raw) if order_price_raw is not None else 0
        except (ValueError, TypeError):
            order_price = 0
            
        try:
            stop_loss_price = float(stop_loss_price_raw) if stop_loss_price_raw is not None else 0
        except (ValueError, TypeError):
            stop_loss_price = 0
        
        if order_size == 0 or order_price == 0:
            return {"valid": False, "reason": "Invalid order parameters (zero or None values)"}
        
        # 1. Check SuperTrend alignment
        supertrend_violation = False
        if order_side == 'buy' and current_supertrend_signal == -1:
            supertrend_violation = True
            reason = "BUY order against SuperTrend SELL signal"
        elif order_side == 'sell' and current_supertrend_signal == 1:
            supertrend_violation = True
            reason = "SELL order against SuperTrend BUY signal"
        
        # 2. Calculate potential loss
        potential_loss = 0
        if order_side == 'buy':
            # For buy orders, loss if price goes down
            potential_loss = (order_price - current_mark_price) * order_size * 0.001
        else:
            # For sell orders, loss if price goes up
            potential_loss = (current_mark_price - order_price) * order_size * 0.001
        
        # 3. Calculate loss percentage of capital
        loss_percentage = (potential_loss / capital) * 100 if capital > 0 else 0
        
        # 4. Check if loss exceeds maximum allowed
        risk_violation = loss_percentage > MAX_CAPITAL_LOSS_PERCENT
        
        # 5. Determine overall validity
        if supertrend_violation and risk_violation:
            return {
                "valid": False, 
                "reason": f"SuperTrend violation ({reason}) AND excessive risk ({loss_percentage:.2f}% loss > {MAX_CAPITAL_LOSS_PERCENT}%)",
                "supertrend_violation": True,
                "risk_violation": True,
                "loss_percentage": loss_percentage
            }
        elif supertrend_violation:
            return {
                "valid": False, 
                "reason": f"SuperTrend violation: {reason}",
                "supertrend_violation": True,
                "risk_violation": False,
                "loss_percentage": loss_percentage
            }
        elif risk_violation:
            return {
                "valid": False, 
                "reason": f"Excessive risk: {loss_percentage:.2f}% potential loss > {MAX_CAPITAL_LOSS_PERCENT}%",
                "supertrend_violation": False,
                "risk_violation": True,
                "loss_percentage": loss_percentage
            }
        else:
            return {
                "valid": True, 
                "reason": f"Order valid - SuperTrend aligned, risk acceptable ({loss_percentage:.2f}%)",
                "supertrend_violation": False,
                "risk_violation": False,
                "loss_percentage": loss_percentage
            }
            
    except Exception as e:
        return {"valid": False, "reason": f"Error validating order: {e}"}

def validate_and_handle_existing_orders(candles, capital):
    """Validate existing orders against current SuperTrend and risk rules"""
    from config import AUTO_CLOSE_INVALID_ORDERS
    
    try:
        # Get current SuperTrend signal
        if candles is None or candles.empty:
            log("⚠️ No candle data available for order validation")
            return False
            
        current_supertrend_signal = int(candles.iloc[-1]['supertrend_signal'])
        current_mark_price = api.get_latest_price()
        
        if current_mark_price is None:
            log("⚠️ Could not get current mark price for order validation")
            return False
        
        # Get existing orders
        live_orders = api.get_live_orders()
        open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
        
        if not open_orders:
            log("✅ No open orders to validate")
            return True
        
        log(f"🔍 Validating {len(open_orders)} existing orders against SuperTrend and risk rules...")
        
        invalid_orders = []
        valid_orders = []
        
        for order in open_orders:
            # Only validate orders for the correct symbol
            if order.get('product_symbol') != SYMBOL:
                continue
                
            validation_result = validate_existing_order_against_strategy(
                order, current_supertrend_signal, current_mark_price, capital
            )
            
            order_id = order.get('id')
            order_side = order.get('side', 'unknown')
            order_size = order.get('size', 0)
            
            if validation_result['valid']:
                valid_orders.append(order)
                log(f"✅ Order {order_id} ({order_side} {order_size}) - {validation_result['reason']}")
            else:
                invalid_orders.append(order)
                log(f"❌ Order {order_id} ({order_side} {order_size}) - {validation_result['reason']}")
        
        # Handle invalid orders
        if invalid_orders and AUTO_CLOSE_INVALID_ORDERS:
            log(f"🚨 Closing {len(invalid_orders)} invalid orders...")
            for order in invalid_orders:
                try:
                    order_id = order.get('id')
                    api.cancel_order(order_id)
                    log(f"   ✅ Cancelled invalid order: {order_id}")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "404" in error_msg or "not found" in error_msg:
                        log(f"   ⚠️ Order {order_id} already cancelled or doesn't exist")
                    else:
                        log(f"   ❌ Failed to cancel invalid order {order_id}: {e}")
            
            # Reset last_order_id if we cancelled the tracked order
            global last_order_id
            cancelled_ids = [order.get('id') for order in invalid_orders]
            if last_order_id in cancelled_ids:
                log(f"🔄 Resetting last_order_id since tracked order was cancelled")
                last_order_id = None
                
        elif invalid_orders:
            log(f"⚠️ Found {len(invalid_orders)} invalid orders but AUTO_CLOSE_INVALID_ORDERS is disabled")
            log(f"   Consider enabling AUTO_CLOSE_INVALID_ORDERS in config.py")
        
        # Return True if we have valid orders or no orders
        return len(valid_orders) > 0 or len(open_orders) == 0
        
    except Exception as e:
        log(f"❌ Error validating existing orders: {e}")
        return False

def validate_and_handle_existing_positions(candles, capital):
    """Validate existing positions against current SuperTrend and risk rules"""
    from config import MAX_CAPITAL_LOSS_PERCENT, AUTO_CLOSE_INVALID_ORDERS
    
    try:
        # Get current SuperTrend signal
        if candles is None or candles.empty:
            log("⚠️ No candle data available for position validation")
            return False
            
        current_supertrend_signal = int(candles.iloc[-1]['supertrend_signal'])
        current_mark_price = api.get_latest_price()
        
        if current_mark_price is None:
            log("⚠️ Could not get current mark price for position validation")
            return False
        
        # Get existing positions with order details
        position_details = get_position_with_order_details()
        
        if not position_details:
            log("✅ No open positions to validate")
            return True
        
        log(f"🔍 Validating {len(position_details)} existing positions against SuperTrend and risk rules...")
        
        invalid_positions = []
        valid_positions = []
        
        for pos_detail in position_details:
            position = pos_detail['position']
            position_size = float(position.get('size', 0))
            entry_price = float(position.get('entry_price', 0))
            
            if position_size == 0 or entry_price == 0:
                continue
                
            # Determine position side
            position_side = pos_detail['side']
            
            # Check SuperTrend alignment
            supertrend_violation = False
            if position_side == 'LONG' and current_supertrend_signal == -1:
                supertrend_violation = True
                reason = "LONG position against SuperTrend SELL signal"
            elif position_side == 'SHORT' and current_supertrend_signal == 1:
                supertrend_violation = True
                reason = "SHORT position against SuperTrend BUY signal"
            
            # Calculate current P&L
            if position_side == 'LONG':
                pnl = (current_mark_price - entry_price) * abs(position_size) * 0.001
            else:
                pnl = (entry_price - current_mark_price) * abs(position_size) * 0.001
            
            # Calculate loss percentage of capital
            loss_percentage = (abs(min(0, pnl)) / capital) * 100 if capital > 0 else 0
            
            # Check if loss exceeds maximum allowed
            risk_violation = loss_percentage > MAX_CAPITAL_LOSS_PERCENT
            
            # Log position details including order ID
            order_info = ""
            if pos_detail['associated_order_id']:
                order_info = f" (Order ID: {pos_detail['associated_order_id']}, State: {pos_detail['order_state']})"
            else:
                order_info = " (No associated order ID - position from filled order)"
            
            if supertrend_violation or risk_violation:
                invalid_positions.append({
                    'position': position,
                    'side': position_side,
                    'size': abs(position_size),
                    'entry_price': entry_price,
                    'current_price': current_mark_price,
                    'pnl': pnl,
                    'loss_percentage': loss_percentage,
                    'supertrend_violation': supertrend_violation,
                    'risk_violation': risk_violation,
                    'reason': reason if supertrend_violation else f"Excessive risk: {loss_percentage:.2f}% loss",
                    'order_id': pos_detail['associated_order_id']
                })
                log(f"❌ Position ({position_side} {abs(position_size)}){order_info} - {reason if supertrend_violation else f'Excessive risk: {loss_percentage:.2f}% loss'}")
            else:
                valid_positions.append(position)
                log(f"✅ Position ({position_side} {abs(position_size)}){order_info} - Valid, P&L: {pnl:.2f}, Risk: {loss_percentage:.2f}%")
        
        # Handle invalid positions
        if invalid_positions and AUTO_CLOSE_INVALID_ORDERS:
            log(f"🚨 Closing {len(invalid_positions)} invalid positions...")
            for invalid_pos in invalid_positions:
                try:
                    position = invalid_pos['position']
                    position_size = float(position.get('size', 0))
                    close_side = 'sell' if position_size > 0 else 'buy'
                    close_size = abs(position_size)
                    
                    # Place market order to close position
                    api.place_order(
                        symbol=SYMBOL,
                        side=close_side,
                        qty=close_size,
                        order_type='market_order',
                        price=None
                    )
                    log(f"   ✅ Closed invalid position: {invalid_pos['side']} {close_size} - {invalid_pos['reason']}")
                except Exception as e:
                    log(f"   ❌ Failed to close invalid position: {e}")
        elif invalid_positions:
            log(f"⚠️ Found {len(invalid_positions)} invalid positions but AUTO_CLOSE_INVALID_ORDERS is disabled")
            log(f"   Consider enabling AUTO_CLOSE_INVALID_ORDERS in config.py")
        
        # Return True if we have valid positions or no positions
        return len(valid_positions) > 0 or len(open_positions) == 0
        
    except Exception as e:
        log(f"❌ Error validating existing positions: {e}")
        return False

def check_and_handle_old_orders():
    """Check for old orders and handle them based on configuration"""
    from config import AUTO_CANCEL_OLD_ORDERS, MAX_ORDER_AGE_HOURS
    import datetime
    
    if not AUTO_CANCEL_OLD_ORDERS:
        return
        
    try:
        live_orders = api.get_live_orders()
        open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
        
        if not open_orders:
            return
            
        current_time = datetime.datetime.now()
        old_orders = []
        
        for order in open_orders:
            created_at = order.get('created_at')
            if created_at:
                try:
                    # Parse the ISO timestamp
                    order_time = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    age_hours = (current_time - order_time).total_seconds() / 3600
                    
                    if age_hours > MAX_ORDER_AGE_HOURS:
                        old_orders.append(order)
                except Exception as e:
                    log(f"⚠️ Could not parse order creation time: {e}")
        
        if old_orders:
            log(f"🕐 Found {len(old_orders)} orders older than {MAX_ORDER_AGE_HOURS} hours")
            for order in old_orders:
                try:
                    api.cancel_order(order['id'])
                    log(f"   Cancelled old order: {order['id']} (age: {order.get('created_at', 'unknown')})")
                except Exception as e:
                    log(f"   Failed to cancel old order {order['id']}: {e}")
        else:
            log(f"✅ All existing orders are within {MAX_ORDER_AGE_HOURS} hours")
            
    except Exception as e:
        log(f"❌ Error checking old orders: {e}")

def should_respect_existing_orders():
    """Check if the bot should respect existing orders or start fresh"""
    from config import RESPECT_EXISTING_ORDERS
    return RESPECT_EXISTING_ORDERS

def handle_existing_orders_strategy():
    """Handle existing orders based on configuration"""
    try:
        live_orders = api.get_live_orders()
        open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
        
        if not open_orders:
            return "no_orders"
            
        # Check if we should respect existing orders
        if should_respect_existing_orders():
            log("📋 Respecting existing orders - bot will work with current orders")
            return "respect_existing"
        else:
            log("🔄 Starting fresh - cancelling existing orders")
            api.cancel_all_orders()
            return "start_fresh"
            
    except Exception as e:
        log(f"❌ Error handling existing orders strategy: {e}")
        return "error"

def check_existing_positions_and_orders():
    """Check for existing positions and orders, and handle edge cases"""
    try:
        state = api.get_account_state(product_id=84)
        has_position = state['has_positions']
        has_order = state['has_orders']
        
        if has_position and not has_order:
            log("⚠️ Found existing positions but no open orders - this might indicate filled orders")
            log("   The bot will continue monitoring and place new orders based on SuperTrend signals")
        elif has_order and not has_position:
            log("⚠️ Found open orders but no positions - orders might be pending")
        elif has_position and has_order:
            log("✅ Found both existing positions and open orders")
        else:
            log("✅ Clean state - no positions or orders")
            
        return state
    except Exception as e:
        log(f"❌ Error checking existing positions and orders: {e}")
        return None

def force_cancel_pending_orders():
    """Force cancel all pending orders with retry mechanism"""
    try:
        # First attempt - use new CancelAllFilterObject API
        result = api.cancel_all_orders_by_product()
        if result.get('success'):
            time.sleep(CANCELLATION_WAIT_TIME)
            if verify_cancellation_success():
                return True
        
        # Second attempt - legacy method
        cancel_success = api.cancel_all_orders()
        if cancel_success:
            time.sleep(CANCELLATION_WAIT_TIME)
            if verify_cancellation_success():
                return True
        
        # Third attempt - individual cancellation
        try:
            live_orders = api.get_live_orders()
            active_orders = [order for order in live_orders if order.get('state') not in ['filled', 'cancelled', 'rejected']]
            
            if not active_orders:
                return True
            
            cancelled_count = 0
            for order in active_orders:
                try:
                    result = api.cancel_order(order['id'])
                    if result and isinstance(result, dict) and result.get('id'):
                        cancelled_count += 1
                    time.sleep(0.5)
                except Exception:
                    pass
            
            time.sleep(CANCELLATION_WAIT_TIME * 1.5)
            return cancelled_count > 0
            
        except Exception:
            return False
            
    except Exception:
        return False

def verify_cancellation_success():
    """Verify that orders are actually cancelled"""
    if not CANCELLATION_VERIFICATION_ENABLED:
        return True
        
    try:
        for attempt in range(CANCELLATION_VERIFICATION_ATTEMPTS):
            try:
                state = api.get_account_state(product_id=84)
                if not state.get('has_orders', True):
                    return True
            except Exception:
                pass
            
            try:
                live_orders = api.get_live_orders()
                active_orders = [order for order in live_orders if order.get('state') not in ['filled', 'cancelled', 'rejected']]
                if not active_orders:
                    return True
            except Exception:
                pass
            
            if attempt < CANCELLATION_VERIFICATION_ATTEMPTS - 1:
                time.sleep(VERIFICATION_WAIT_TIME)
        
        return False
        
    except Exception:
        return False

def verify_order_id_match(order_id, expected_order_id=None):
    """Verify that the order ID matches what's expected or visible on the platform"""
    try:
        # Get the order details from the exchange
        live_orders = api.get_live_orders()
        
        # Look for the order by ID
        found_order = None
        for order in live_orders:
            if order.get('id') == order_id:
                found_order = order
                break
        
        if found_order:
            log(f"✅ Order ID {order_id} verified on exchange")
            log(f"   Order details: {found_order.get('side', 'unknown')} {found_order.get('size', 0)} @ {found_order.get('limit_price', 'unknown')}")
            log(f"   State: {found_order.get('state', 'unknown')}")
            log(f"   Product: {found_order.get('product_symbol', 'unknown')}")
            
            if expected_order_id and order_id != expected_order_id:
                log(f"⚠️ Order ID mismatch: Bot got {order_id}, Expected {expected_order_id}")
                return False
            return True
        else:
            log(f"❌ Order ID {order_id} not found on exchange")
            
            # List all available order IDs for debugging
            available_ids = [order.get('id') for order in live_orders]
            log(f"   Available order IDs on exchange: {available_ids}")
            return False
            
    except Exception as e:
        log(f"❌ Error verifying order ID {order_id}: {e}")
        return False

def get_position_with_order_details():
    """Get position details with associated order information"""
    try:
        positions = api.get_positions(product_id=84)
        if not positions:
            return []
        
        if isinstance(positions, dict):
            positions = [positions]
        
        open_positions = [pos for pos in positions if isinstance(pos, dict) and float(pos.get('size', 0)) != 0]
        
        if not open_positions:
            return []
        
        # Get all orders to find associated order IDs
        live_orders = api.get_live_orders()
        
        position_details = []
        for pos in open_positions:
            pos_size = float(pos.get('size', 0))
            pos_side = 'LONG' if pos_size > 0 else 'SHORT'
            
            # Try to find associated order by matching size and side
            associated_order = None
            for order in live_orders:
                order_size = float(order.get('size', 0))
                order_side = order.get('side', '').upper()
                
                # Match order with position
                if (abs(order_size) == abs(pos_size) and 
                    ((order_side == 'BUY' and pos_side == 'LONG') or 
                     (order_side == 'SELL' and pos_side == 'SHORT'))):
                    associated_order = order
                    break
            
            position_info = {
                'position': pos,
                'side': pos_side,
                'size': abs(pos_size),
                'entry_price': pos.get('entry_price', 'unknown'),
                'mark_price': pos.get('mark_price', 'unknown'),
                'unrealized_pnl': pos.get('unrealized_pnl', 'unknown'),
                'associated_order_id': associated_order.get('id') if associated_order else None,
                'order_state': associated_order.get('state') if associated_order else None,
                'order_created_at': associated_order.get('created_at') if associated_order else None
            }
            position_details.append(position_info)
        
        return position_details
    except Exception as e:
        log(f"❌ Error getting position details: {e}")
        return []

def check_specific_order_id(target_order_id):
    """Check if a specific order ID exists in the order history"""
    try:
        live_orders = api.get_live_orders()
        for order in live_orders:
            if order.get('id') == target_order_id:
                log(f"🎯 Found target order ID {target_order_id} with state: {order.get('state')}")
                log(f"   Order details: {order.get('side', 'unknown')} {order.get('size', 0)} @ {order.get('limit_price', 'unknown')}")
                return order
        log(f"🔍 Target order ID {target_order_id} not found in current order list")
        return None
    except Exception as e:
        log(f"❌ Error checking for specific order ID {target_order_id}: {e}")
        return None

def initialize_order_tracking():
    """Initialize last_order_id by checking for existing orders and positions when bot starts"""
    global last_order_id
    try:
        # First, check for existing positions with order details
        position_details = get_position_with_order_details()
        
        if position_details:
            log(f"🔍 Found {len(position_details)} existing positions with order details:")
            for pos_detail in position_details:
                log(f"   Position: {pos_detail['side']} {pos_detail['size']} @ {pos_detail['entry_price']}")
                log(f"   Mark Price: {pos_detail['mark_price']}, P&L: {pos_detail['unrealized_pnl']}")
                if pos_detail['associated_order_id']:
                    log(f"   Associated Order ID: {pos_detail['associated_order_id']} (State: {pos_detail['order_state']})")
                    log(f"   Order Created: {pos_detail['order_created_at']}")
                else:
                    log(f"   Associated Order ID: None (position may be from filled order)")
            
            # Check for specific order ID 662775126 (the one you mentioned)
            specific_order = check_specific_order_id(662775126)
            if specific_order:
                last_order_id = 662775126
                log(f"✅ Using specific order ID {last_order_id} for position tracking")
                return True
            
            # Use the first associated order ID if available
            for pos_detail in position_details:
                if pos_detail['associated_order_id']:
                    last_order_id = pos_detail['associated_order_id']
                    log(f"✅ Using associated order ID {last_order_id} for position tracking")
                    return True
            
            # If no associated order ID found, use position tracking
            log("🔍 Found existing positions but no associated order IDs - using position tracking")
            log("   This means the positions were created by filled orders that are no longer in the order history")
            last_order_id = None
            return True
        
        # If no positions, check for open orders
        live_orders = api.get_live_orders()
        open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
        if open_orders:
            # Sort by creation time to get the most recent order
            open_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            most_recent_order = open_orders[0]
            last_order_id = most_recent_order.get('id')
            
            # Validate the order is for the correct symbol
            if most_recent_order.get('product_symbol') == SYMBOL:
                log(f"🔍 Found existing open order on startup: {last_order_id}")
                log(f"   Order details: {most_recent_order.get('side', 'unknown')} {most_recent_order.get('size', 0)} @ {most_recent_order.get('limit_price', 'unknown')}")
                log(f"   Stop Loss: {most_recent_order.get('bracket_stop_loss_price', 'none')}")
                log(f"   Take Profit: {most_recent_order.get('bracket_take_profit_price', 'none')}")
                return True
            else:
                log(f"⚠️ Found existing order for different symbol: {most_recent_order.get('product_symbol')}")
                log(f"   Expected: {SYMBOL}, Found: {most_recent_order.get('product_symbol')}")
                log(f"   Consider cancelling this order if it's not needed")
                last_order_id = None
                return False
        else:
            log("🔍 No existing orders or positions found on startup")
            last_order_id = None
            return False
    except Exception as e:
        log(f"❌ Error checking for existing orders on startup: {e}")
        last_order_id = None
        return False

def get_current_order_id():
    """Retrieve the current order ID from the exchange as a fallback"""
    try:
        # First check for open orders
        live_orders = api.get_live_orders()
        open_orders = [order for order in live_orders if order.get('state') in ['open', 'pending']]
        if open_orders:
            # Sort by creation time to get the most recent order
            open_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            order_id = open_orders[0].get('id')
            log(f"🔄 Retrieved open order ID from exchange: {order_id}")
            log(f"   Found {len(open_orders)} open orders, using most recent")
            return order_id
        
        # If no open orders, check for filled orders (for existing positions)
        filled_orders = [order for order in live_orders if order.get('state') in ['filled', 'closed']]
        if filled_orders:
            # Sort by creation time to get the most recent filled order
            filled_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            order_id = filled_orders[0].get('id')
            log(f"🔄 Retrieved filled order ID from exchange: {order_id}")
            log(f"   Found {len(filled_orders)} filled orders, using most recent")
            return order_id
        
        log("🔄 No orders found in exchange")
        return None
    except Exception as e:
        log(f"❌ Error retrieving current order ID: {e}")
        return None

def execute_trade_optimized(decision):
    if not decision or not decision['action']:
        return False
    log(f"🚀 Trade triggered: {decision['action']} {decision['side']} {decision['qty']} at Price: ${decision['price']:.2f} -- Stop-Loss at {decision['stop_loss']}")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            cancel_future = executor.submit(api.cancel_all_orders)
            close_future = executor.submit(api.close_all_positions, 84)
            cancel_success = cancel_future.result(timeout=5)
            close_success = close_future.result(timeout=5)
            if not cancel_success:
                log("❌ Critical Error: Could not cancel orders")
                return False
            if not close_success:
                log("❌ Critical Error: Could not close positions")
                return False
            api_side = 'buy' if decision['side'] == 'LONG' else 'sell'
            take_profit = decision['price'] + ((decision['price'] - decision['stop_loss']) * TAKE_PROFIT_MULTIPLIER)
        if api_side == 'buy':
            order_price = decision['price'] + ORDER_PRICE_OFFSET
        else:
            order_price = decision['price'] - ORDER_PRICE_OFFSET
        post_only = False
        start_order_time = time.time()
        result = api.place_order(
            symbol=SYMBOL,
            side=api_side,
            qty=decision['qty'],
            price=order_price,
            stop_loss=decision['stop_loss'],
            take_profit=take_profit,
            post_only=post_only
        )
        global last_order_id
        # Enhanced order ID extraction with verification
        if isinstance(result, dict) and 'id' in result:
            last_order_id = result['id']
            log(f"📝 Order ID captured: {last_order_id}")
            
            # Verify the order ID on the exchange
            log(f"🔍 Verifying order ID {last_order_id} on exchange...")
            if verify_order_id_match(last_order_id):
                log(f"✅ Order ID {last_order_id} verified successfully")
            else:
                log(f"⚠️ Order ID {last_order_id} verification failed - checking for alternatives")
                # Try to find the actual order on the exchange
                fallback_order_id = get_current_order_id()
                if fallback_order_id and fallback_order_id != last_order_id:
                    log(f"🔄 Using fallback order ID: {fallback_order_id} (original: {last_order_id})")
                    last_order_id = fallback_order_id
        else:
            log(f"⚠️ Warning: Could not extract order ID from result: {result}")
            last_order_id = None
        elapsed = time.time() - start_order_time
        log(f"✅ Main at {order_price} and Bracket stop loss at {decision['stop_loss']} orders placed successfully in {elapsed:.2f}s")
        if elapsed > 2.0:
            log(f"⚠️  Trade execution exceeded 2s: {elapsed:.2f}s")
        return True
    except Exception as e:
        log(f"❌ Error placing order: {e}")
        return False

print('Starting optimized live trading loop...')

# Initialize order tracking on startup
log("🚀 Initializing order tracking...")
check_existing_positions_and_orders()
check_and_handle_old_orders()  # Check for old orders before deciding strategy
order_strategy = handle_existing_orders_strategy()
if order_strategy == "respect_existing":
    initialize_order_tracking()
elif order_strategy == "start_fresh":
    log("🔄 Starting with clean slate - no existing orders to track")
    last_order_id = None
elif order_strategy == "no_orders":
    log("✅ No existing orders found - ready to start trading")
    last_order_id = None

# Note: Order validation will be done in the main loop after getting candle data

# Align to next candle
while True:
    now = datetime.datetime.now()
    if now.minute % CANDLE_INTERVAL == 0 and now.second == 0:
        break
    next_minute = (now.minute // CANDLE_INTERVAL + 1) * CANDLE_INTERVAL
    if next_minute >= 60:
        next_time = now.replace(hour=(now.hour + 1) % 24, minute=0, second=0, microsecond=0)
    else:
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)
    wait_seconds = (next_time - now).total_seconds()
    print(f"Waiting for next candle alignment... ({next_time.strftime('%Y-%m-%d %H:%M:%S')})")
    time.sleep(wait_seconds)

# Main trading loop
while True:
    iteration_start = time.time()
    try:
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        
        # Fetch and validate candle data
        candles = fetch_candles_optimized()
        if candles is None or (isinstance(candles, pd.DataFrame) and candles.empty):
            if CANDLE_FALLBACK_ENABLED:
                log("No Delta Exchange candle data, trying Binance as fallback...")
                binance_candles = api.get_candles_binance(symbol='BTCUSDT', interval=f'{CANDLE_INTERVAL}m', limit=100)
                if binance_candles is None or len(binance_candles) == 0:
                    log("No Binance candle data either. Skipping iteration.")
                    time.sleep(30)
                    continue
                candles = pd.DataFrame(binance_candles)
                candles['datetime'] = pd.to_datetime(candles['time'], unit='s')
                candles = candles.sort_values('datetime')
            else:
                log("No Delta Exchange candle data and fallback is disabled. Skipping iteration.")
                time.sleep(30)
                continue
                
        # Calculate SuperTrend
        candles = calculate_supertrend_optimized(candles)
        if candles is None:
            log("Skipping iteration due to SuperTrend calculation error")
            time.sleep(30)
            continue
            
        # Validate existing orders and positions
        current_capital = get_current_capital()
        order_validation_success = validate_and_handle_existing_orders(candles, current_capital)
        position_validation_success = validate_and_handle_existing_positions(candles, current_capital)
        
        if not order_validation_success:
            log("⚠️ Order validation failed, continuing with trading logic")
        if not position_validation_success:
            log("⚠️ Position validation failed, continuing with trading logic")
            
        # Get current signals
        if len(candles) < 2:
            log("⚠️ Insufficient candle data for signal generation")
            time.sleep(30)
            continue
            
        last_signal = int(candles.iloc[-1]['supertrend_signal'])
        prev_signal = int(candles.iloc[-2]['supertrend_signal']) if len(candles) > 1 else last_signal
        
        # Get account state
        try:
            state = api.get_account_state(product_id=84)
            has_position = state['has_positions']
            has_order = state['has_orders']
        except Exception as e:
            log(f"❌ Error getting account state: {e}")
            time.sleep(30)
            continue
            
        # Main trading logic
        if has_position:
            if prev_supertrend_signal is not None and last_signal != prev_supertrend_signal:
                log("SuperTrend direction changed. Closing current position and opening new one.")
                try:
                    api.close_all_positions(84)
                    decision = run_strategy_optimized(candles, capital)
                    if decision and decision['action']:
                        execute_trade_optimized(decision)
                        pending_order_iterations = 0
                except Exception as e:
                    log(f"❌ Error handling SuperTrend change: {e}")
            else:
                latest_supertrend = candles.iloc[-1]['supertrend']
                if last_order_id is not None:
                    try:
                        api.edit_bracket_order(order_id=last_order_id, stop_loss=latest_supertrend)
                        log(f"Updated stop loss to latest SuperTrend value: {latest_supertrend} for order {last_order_id}")
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "404" in error_msg or "not found" in error_msg or "does not exist" in error_msg:
                            log(f"Order {last_order_id} no longer exists, resetting last_order_id")
                            last_order_id = None
                        else:
                            log(f"Failed to update stop loss for order {last_order_id}: {e}")
                else:
                    # Try to retrieve order ID from exchange as fallback
                    fallback_order_id = get_current_order_id()
                    if fallback_order_id is not None:
                        try:
                            api.edit_bracket_order(order_id=fallback_order_id, stop_loss=latest_supertrend)
                            log(f"Updated stop loss using fallback order ID: {latest_supertrend} for order {fallback_order_id}")
                            last_order_id = fallback_order_id  # Update our tracking
                        except Exception as e:
                            error_msg = str(e).lower()
                            if "404" in error_msg or "not found" in error_msg or "does not exist" in error_msg:
                                log(f"Fallback order {fallback_order_id} no longer exists")
                                last_order_id = None
                            else:
                                log(f"Failed to update stop loss with fallback order ID {fallback_order_id}: {e}")
                    else:
                        log(f"No last_order_id available to update stop loss.")
                prev_supertrend_signal = last_signal
                time.sleep(CANDLE_INTERVAL * 60)
                continue
        elif not has_order:
            log("No active order. Placing new order based on SuperTrend signal.")
            try:
                decision = run_strategy_optimized(candles, capital)
                if decision and decision['action']:
                    execute_trade_optimized(decision)
                    pending_order_iterations = 0
            except Exception as e:
                log(f"❌ Error placing new order: {e}")
        else:
            pending_order_iterations += 1
            log(f"Pending order detected. Iteration count: {pending_order_iterations}")
            if pending_order_iterations >= PENDING_ORDER_MAX_ITERATIONS:
                log("Pending order not filled after multiple iterations. Force cancelling and placing new order.")
                try:
                    # Force cancel all orders with retry mechanism
                    cancel_success = force_cancel_pending_orders()
                    
                    if cancel_success:
                        log("✅ Orders cancelled successfully")
                        
                        # Verify cancellation and place new order
                        if verify_cancellation_success():
                            decision = run_strategy_optimized(candles, capital)
                            if decision and decision['action']:
                                execute_trade_optimized(decision)
                        else:
                            log("⚠️ Orders still exist after force cancellation - skipping new order placement")
                        
                        pending_order_iterations = 0  # Reset counter to avoid infinite loop
                    else:
                        log("❌ Failed to cancel orders even with force cancellation")
                        log("   Manual intervention may be required to cancel orders on the platform")
                        pending_order_iterations = 0  # Reset counter to avoid infinite loop
                        
                except Exception as e:
                    log(f"❌ Error handling pending order timeout: {e}")
                    pending_order_iterations = 0  # Reset counter to avoid infinite loop
                    
        prev_supertrend_signal = last_signal
        iteration_time = time.time() - iteration_start
        if iteration_time > MAX_ITERATION_TIME:
            log(f"⚠️  Slow iteration: {iteration_time:.2f}s")
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log(f'Waiting for next candle... ({now_str}) - Iteration time: {iteration_time:.2f}s')
        time.sleep(CANDLE_INTERVAL * 60)
    except Exception as e:
        log(f"❌ Critical error in main loop: {e}")
        time.sleep(5)
