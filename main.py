import time
import pandas as pd
from delta_api import DeltaAPI
from supertrend import calculate_supertrend
from live_strategy import LiveStrategy
from notify import send_trade_email
from config import SYMBOL, CANDLE_INTERVAL, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER
import datetime
import os
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# Initialize optimized modules
api = DeltaAPI()
strategy = LiveStrategy(api)
capital = 200
candles = pd.DataFrame()

print('Starting optimized live trading loop...')

# Fix the alignment loop at the start of the script
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

def fetch_candles_optimized():
    """Optimized candle fetching with error handling"""
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
        print(f"Error fetching candles: {e}")
        return None

def calculate_supertrend_optimized(candles):
    """Optimized SuperTrend calculation"""
    try:
        return calculate_supertrend(candles, period=SUPERTREND_PERIOD, multiplier=SUPERTREND_MULTIPLIER)
    except Exception as e:
        print(f"Error calculating SuperTrend: {e}")
        return None

def run_strategy_optimized(candles, capital):
    """Optimized strategy execution"""
    try:
        return strategy.decide(candles, capital)
    except Exception as e:
        print(f"Error in strategy decision: {e}")
        return None

def execute_trade_optimized(decision):
    """Optimized trade execution for <2s latency, with parallel cleanup and fast order placement."""
    if not decision or not decision['action']:
        return False
    
    log(f"🚀 Trade triggered: {decision['action']} {decision['side']} {decision['qty']} at ${decision['price']:.2f} -- Stop-Loss at {decision['stop_loss']}")
    try:
        # Start parallel cleanup
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            cancel_future = executor.submit(api.cancel_all_orders)
            close_future = executor.submit(api.close_all_positions, 84)
            # Wait for both to complete (as fast as possible)
            cancel_success = cancel_future.result(timeout=5)
            close_success = close_future.result(timeout=5)
            if not cancel_success:
                log("❌ Critical Error: Could not cancel orders")
                return False
            if not close_success:
                log("❌ Critical Error: Could not close positions")
                return False
        # Place new order with short timeout
        try:
            api_side = 'buy' if decision['side'] == 'LONG' else 'sell'
            take_profit = decision['price'] + ((decision['price'] - decision['stop_loss']) * 1.5)
            # Fetch best bid/ask
            best_bid, best_ask = get_best_bid_ask()
            order_price = decision['price']
            post_only = True
            if api_side == 'buy' and best_bid is not None:
                # Set price just below best bid
                if order_price >= best_bid:
                    order_price = best_bid - 0.5  # or tick size
                if order_price >= best_ask:
                    # Would cross the spread, fallback to non-post-only
                    post_only = False
            elif api_side == 'sell' and best_ask is not None:
                # Set price just above best ask
                if order_price <= best_ask:
                    order_price = best_ask + 0.5  # or tick size
                if order_price <= best_bid:
                    post_only = False
            result = api.place_order(
                symbol=SYMBOL,
                side=api_side,
                qty=decision['qty'],
                price=order_price,
                stop_loss=decision['stop_loss'],
                take_profit=take_profit,
                post_only=post_only
            )
            # Store the order_id for later stop loss updates
            global last_order_id
            last_order_id = result.get('id') if isinstance(result, dict) else None
            elapsed = time.time() - start_order_time
            log(f"✅ Main and Bracket stop loss orders placed successfully in {elapsed:.2f}s")
            if elapsed > 2.0:
                log(f"⚠️  Trade execution exceeded 2s: {elapsed:.2f}s")
            return True
        except Exception as e:
            log(f"❌ Error placing order: {e}")
            return False
    except Exception as e:
        log(f"❌ Error in trade execution: {e}")
        return False

def send_notification_async(subject, body):
    """Send notification asynchronously"""
    # try:
    #     # Run notification in a separate thread to avoid blocking
    #     with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    #         future = executor.submit(send_trade_email, subject, body)
    #         # Don't wait for completion - fire and forget
    #         return True
    # except Exception as e:
    #     print(f"Warning: Could not send notification: {e}")
    #     return False

# --- New state tracking variables for enhanced logic ---
prev_supertrend_signal = None
pending_order_iterations = 0
last_order_id = None

# Add a function to get the best bid/ask from the order book

def get_best_bid_ask():
    try:
        # Fetch order book from Delta Exchange
        url = f"{api.BASE_URL}/v2/l2orderbook/{SYMBOL}"
        r = api.session.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data.get("success") and data.get("result"):
            bids = data["result"].get("buy", [])
            asks = data["result"].get("sell", [])
            best_bid = float(bids[0][0]) if bids else None
            best_ask = float(asks[0][0]) if asks else None
            return best_bid, best_ask
    except Exception as e:
        log(f"Error fetching order book: {e}")
    return None, None

# Main optimized trading loop
while True:
    iteration_start = time.time()
    try:
        # Step 1: Fetch candles (optimized)
        # Align current time to the start of the minute (seconds = 0)
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        candles = fetch_candles_optimized()
        if candles is None or (isinstance(candles, pd.DataFrame) and candles.empty):
            log("No Delta Exchange candle data, trying Binance as fallback...")
            binance_candles = api.get_candles_binance(symbol='BTCUSDT', interval=f'{CANDLE_INTERVAL}m', limit=100)
            if binance_candles is None or len(binance_candles) == 0:
                log("No Binance candle data either. Skipping iteration.")
                time.sleep(30)
                continue
            candles = pd.DataFrame(binance_candles)
            candles['datetime'] = pd.to_datetime(candles['time'], unit='s')
            candles = candles.sort_values('datetime')

        # Step 2: Calculate SuperTrend (optimized)
        candles = calculate_supertrend_optimized(candles)
        if candles is None:
            log("Skipping iteration due to SuperTrend calculation error")
            time.sleep(30)
            continue

        # Step 3: Get SuperTrend signals
        last_signal = int(candles.iloc[-1]['supertrend_signal'])
        prev_signal = int(candles.iloc[-2]['supertrend_signal']) if len(candles) > 1 else last_signal

        # Step 4: Get account state
        state = api.get_account_state(product_id=84)
        has_position = state['has_positions']
        has_order = state['has_orders']

        # --- Enhanced trading logic ---
        if has_position:
            # There is an open position
            if prev_supertrend_signal is not None and last_signal != prev_supertrend_signal:
                log("SuperTrend direction changed. Closing current position and opening new one.")
                api.close_all_positions(84)
                # Place new order in the new direction
                decision = run_strategy_optimized(candles, capital)
                if decision and decision['action']:
                    execute_trade_optimized(decision)
                    pending_order_iterations = 0
                    last_order_id = None
            else:
                # Update stop loss to latest supertrend value
                latest_supertrend = candles.iloc[-1]['supertrend']
                if last_order_id is not None:
                    try:
                        api.edit_bracket_order(order_id=last_order_id, stop_loss=latest_supertrend)
                        log(f"Updated stop loss to latest SuperTrend value: {latest_supertrend} for order {last_order_id}")
                    except Exception as e:
                        log(f"Failed to update stop loss for order {last_order_id}: {e}")
                else:
                    log(f"No last_order_id available to update stop loss.")
                prev_supertrend_signal = last_signal
                time.sleep(CANDLE_INTERVAL * 60)
                continue
        elif not has_order:
            # No active order or position
            log("No active order. Placing new order based on SuperTrend signal.")
            decision = run_strategy_optimized(candles, capital)
            if decision and decision['action']:
                execute_trade_optimized(decision)
                pending_order_iterations = 0
                last_order_id = None
        else:
            # There is a pending order but no position
            pending_order_iterations += 1
            log(f"Pending order detected. Iteration count: {pending_order_iterations}")
            if pending_order_iterations >= 3:
                log("Pending order not filled after 3 iterations. Cancelling and placing new order.")
                api.cancel_all_orders()
                decision = run_strategy_optimized(candles, capital)
                if decision and decision['action']:
                    execute_trade_optimized(decision)
                pending_order_iterations = 0
                last_order_id = None

        prev_supertrend_signal = last_signal

        # Performance monitoring
        iteration_time = time.time() - iteration_start
        if iteration_time > 2.0:
            log(f"⚠️  Slow iteration: {iteration_time:.2f}s")
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log(f'Waiting for next candle... ({now_str}) - Iteration time: {iteration_time:.2f}s')
        time.sleep(CANDLE_INTERVAL * 60)

    except Exception as e:
        log(f"Error in main loop: {e}")
        time.sleep(5)  # Reduced sleep time for faster recovery
