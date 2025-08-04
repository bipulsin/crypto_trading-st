#!/usr/bin/env python3
"""
Delta Exchange Trading Report Generator
Extracts all trading data from Delta Exchange India and builds a comprehensive trade report
with proper entry/exit pairing for complete trades.
"""

import pandas as pd
import requests
import time
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, timedelta
from config import API_KEY, API_SECRET, BASE_URL, SYMBOL_ID
from logger import get_logger
import io

# Set up logger
logger = get_logger('deltareport', 'logs/deltareport.log')

def sign_request(method, path, body=None):
    """Sign request for Delta Exchange API"""
    timestamp = str(int(time.time()))
    if body is None:
        body = ""
    else:
        body = json.dumps(body)
    message = method + timestamp + path + body
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    headers = {
        "api-key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }
    return headers, timestamp, message, signature

def get_all_closed_orders(product_id=None, max_orders=10000):
    """
    Get all closed orders from Delta Exchange
    
    Args:
        product_id (int, optional): Product ID to filter by. If None, uses SYMBOL_ID from config
        max_orders (int): Maximum number of orders to fetch
        
    Returns:
        list: List of closed orders
    """
    if product_id is None:
        product_id = SYMBOL_ID
    
    try:
        all_orders = []
        offset = 0
        limit = 10  # API seems to return max 10 orders per request
        
        logger.info(f"Fetching closed orders for product_id: {product_id}")
        
        while len(all_orders) < max_orders:
            path = f"/v2/orders/history?limit={limit}&offset={offset}&state=closed"
            if product_id:
                path += f"&product_id={product_id}"
            
            # logger.info(f"Fetching orders with offset: {offset}")
            
            headers, timestamp, message, signature = sign_request("GET", path)
            
            session = requests.Session()
            r = session.get(BASE_URL + path, headers=headers, timeout=30)
            
            if r.status_code != 200:
                logger.error(f"API Error: {r.status_code} - {r.text}")
                if r.status_code == 500:
                    logger.warning("Server error (500) - stopping pagination")
                    break
                break
            
            data = r.json()
            if not data.get('success', False):
                logger.error(f"API returned error: {data}")
                break
            
            orders_data = data.get('result', [])
            
            # Handle different response formats
            if isinstance(orders_data, dict):
                orders = orders_data.get('result', [])
            else:
                orders = orders_data if isinstance(orders_data, list) else []
            
            if not orders:
                logger.info("No more orders to fetch")
                break
            
            all_orders.extend(orders)
            logger.info(f"Fetched {len(orders)} orders, total: {len(all_orders)}")
            
            offset += limit
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        logger.info(f"Total closed orders fetched: {len(all_orders)}")
        return all_orders
        
    except Exception as e:
        logger.error(f"Error fetching closed orders: {e}")
        return []

def determine_order_type(order):
    """
    Determine if an order is an entry or exit order
    
    Args:
        order (dict): Order data from API
        
    Returns:
        str: 'entry' or 'exit'
    """
    try:
        # Add debugging for first few orders
        if 'debug_order_count' not in globals():
            globals()['debug_order_count'] = 0
        
        if globals()['debug_order_count'] < 3:
            logger.info(f"Debug Order {globals()['debug_order_count']}: {order}")
            globals()['debug_order_count'] += 1
        
        # Check if it's a reduce-only order (exit)
        if order.get('reduce_only', False):
            logger.debug(f"Order {order.get('id', 'unknown')} classified as exit (reduce_only)")
            return 'exit'
        
        # Check if it's a bracket order (exit)
        if order.get('bracket_order', False):
            logger.debug(f"Order {order.get('id', 'unknown')} classified as exit (bracket_order)")
            return 'exit'
        
        # Check meta_data for P&L info (exit orders often have P&L)
        meta_data = order.get('meta_data', {})
        if meta_data and isinstance(meta_data, dict) and 'pnl' in meta_data:
            logger.debug(f"Order {order.get('id', 'unknown')} classified as exit (has P&L in meta_data)")
            return 'exit'
        
        # Check order type - be more specific about exit order types
        order_type = order.get('order_type', '').lower()
        if order_type in ['stop', 'stop_market', 'take_profit', 'take_profit_market']:
            logger.debug(f"Order {order.get('id', 'unknown')} classified as exit (order_type: {order_type})")
            return 'exit'
        
        # Check if order has a specific exit indicator
        if order.get('is_close', False):
            logger.debug(f"Order {order.get('id', 'unknown')} classified as exit (is_close)")
            return 'exit'
        
        # Check side and context - if it's a sell order and we have a long position, it's likely an exit
        # This is a more nuanced approach
        side = order.get('side', '').lower()
        
        # For now, let's be conservative and classify based on order type
        # Market and limit orders are typically entries unless they have specific exit indicators
        if order_type in ['market', 'limit']:
            logger.debug(f"Order {order.get('id', 'unknown')} classified as entry (order_type: {order_type})")
            return 'entry'
        
        # Default to entry for unknown order types
        logger.debug(f"Order {order.get('id', 'unknown')} classified as entry (default)")
        return 'entry'
        
    except Exception as e:
        logger.error(f"Error determining order type: {e}")
        return 'entry'

def determine_order_side(order):
    """
    Determine the order side classification
    
    Args:
        order (dict): Order data from API
        
    Returns:
        str: 'Open Buy', 'Close Sell', 'Open Sell', 'Close Buy'
    """
    try:
        side = order.get('side', '').lower()
        order_type = determine_order_type(order)
        
        if order_type == 'entry':
            if side == 'buy':
                return 'Open Buy'
            elif side == 'sell':
                return 'Open Sell'
        else:  # exit
            if side == 'sell':
                return 'Close Sell'
            elif side == 'buy':
                return 'Close Buy'
        
        # Fallback - if we can't determine order type, use side as fallback
        if side == 'buy':
            return 'Open Buy'
        else:
            return 'Open Sell'
            
    except Exception as e:
        logger.error(f"Error determining order side: {e}")
        return 'Unknown'

def convert_to_india_time(utc_time_str):
    """
    Convert UTC datetime string to India Standard Time
    
    Args:
        utc_time_str (str): UTC datetime string
        
    Returns:
        str: IST datetime string
    """
    try:
        # Parse UTC time
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # Convert to IST (UTC+5:30)
        ist_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        
        return ist_time.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        logger.error(f"Error converting time: {e}")
        return utc_time_str

def pair_trades(orders):
    """
    Pair entry and exit orders into complete trades
    
    Args:
        orders (list): List of order dictionaries
        
    Returns:
        pd.DataFrame: DataFrame with paired trades
    """
    try:
        if not orders:
            logger.warning("No orders provided")
            return pd.DataFrame()
        
        df = pd.DataFrame(orders)
        
        # Validate required columns exist
        required_columns = ['id', 'side', 'size', 'average_fill_price', 'created_at']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")
            return pd.DataFrame()
        
        # Filter out cancelled orders (those with None average_fill_price)
        df = df[df['average_fill_price'].notna()].copy()
        logger.info(f"After filtering cancelled orders: {len(df)} orders")
        
        if df.empty:
            logger.warning("No valid orders after filtering")
            return pd.DataFrame()
        
        # Add order classification
        df['order_type'] = df.apply(determine_order_type, axis=1)
        df['order_side'] = df.apply(determine_order_side, axis=1)
        
        # Add debugging to understand order classification
        logger.info("Sample order classification:")
        sample_orders = df.head(5)
        for idx, order in sample_orders.iterrows():
            order_id = order.get('id', 'unknown') if hasattr(order, 'get') else order['id']
            side = order.get('side', 'unknown') if hasattr(order, 'get') else order['side']
            order_type = order.get('order_type', 'unknown') if hasattr(order, 'get') else order['order_type']
            classified_as = order['order_side']
            logger.info(f"  Order {order_id}: side={side}, order_type={order_type}, classified_as={classified_as}")
        
        # Parse datetime with error handling
        try:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df = df.dropna(subset=['created_at'])
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            return pd.DataFrame()
        
        if df.empty:
            logger.warning("No orders with valid datetime after parsing")
            return pd.DataFrame()
        
        # Sort by creation time
        df = df.sort_values('created_at').reset_index(drop=True)
        
        logger.info("Order classification breakdown:")
        logger.info(f"  Open Buy: {len(df[df['order_side'] == 'Open Buy'])}")
        logger.info(f"  Close Sell: {len(df[df['order_side'] == 'Close Sell'])}")
        logger.info(f"  Open Sell: {len(df[df['order_side'] == 'Open Sell'])}")
        logger.info(f"  Close Buy: {len(df[df['order_side'] == 'Close Buy'])}")
        
        # If we have no entry orders, let's try a different approach
        if len(df[df['order_side'].isin(['Open Buy', 'Open Sell'])]) == 0:
            logger.warning("No entry orders found! Trying alternative classification...")
            
            # Alternative approach: classify based on chronological order and side
            # Assume we have alternating buy/sell orders
            df_sorted = df.sort_values('created_at').reset_index(drop=True)
            
            # Simple heuristic: if we have more sell orders than buy orders, 
            # the first orders are likely entries
            buy_orders = df_sorted[df_sorted['side'].str.lower() == 'buy']
            sell_orders = df_sorted[df_sorted['side'].str.lower() == 'sell']
            
            logger.info(f"Alternative analysis: {len(buy_orders)} buy orders, {len(sell_orders)} sell orders")
            
            # If we have roughly equal numbers, assume first half are entries
            if abs(len(buy_orders) - len(sell_orders)) <= 100:  # Allow some tolerance
                logger.info("Roughly equal buy/sell orders - using chronological classification")
                
                # Classify first half as entries, second half as exits
                mid_point = len(df_sorted) // 2
                
                for idx, order in df_sorted.iterrows():
                    side = order.get('side', '').lower() if hasattr(order, 'get') else order['side'].lower()
                    if idx < mid_point:
                        # First half - entries
                        if side == 'buy':
                            df_sorted.loc[idx, 'order_side'] = 'Open Buy'
                        else:
                            df_sorted.loc[idx, 'order_side'] = 'Open Sell'
                    else:
                        # Second half - exits
                        if side == 'sell':
                            df_sorted.loc[idx, 'order_side'] = 'Close Sell'
                        else:
                            df_sorted.loc[idx, 'order_side'] = 'Close Buy'
                
                df = df_sorted
                logger.info("Alternative classification applied")
                logger.info("Updated order classification breakdown:")
                logger.info(f"  Open Buy: {len(df[df['order_side'] == 'Open Buy'])}")
                logger.info(f"  Close Sell: {len(df[df['order_side'] == 'Close Sell'])}")
                logger.info(f"  Open Sell: {len(df[df['order_side'] == 'Open Sell'])}")
                logger.info(f"  Close Buy: {len(df[df['order_side'] == 'Close Buy'])}")
            else:
                # If we have significantly different numbers, use a different approach
                logger.info("Unequal buy/sell orders - using pattern-based classification")
                
                # Look for patterns in the data
                # If we have more sell orders, assume we're closing long positions
                # If we have more buy orders, assume we're closing short positions
                
                if len(sell_orders) > len(buy_orders):
                    logger.info("More sell orders - assuming closing long positions")
                    # Classify buy orders as entries, sell orders as exits
                    for idx, order in df_sorted.iterrows():
                        side = order.get('side', '').lower() if hasattr(order, 'get') else order['side'].lower()
                        if side == 'buy':
                            df_sorted.loc[idx, 'order_side'] = 'Open Buy'
                        else:
                            df_sorted.loc[idx, 'order_side'] = 'Close Sell'
                else:
                    logger.info("More buy orders - assuming closing short positions")
                    # Classify sell orders as entries, buy orders as exits
                    for idx, order in df_sorted.iterrows():
                        side = order.get('side', '').lower() if hasattr(order, 'get') else order['side'].lower()
                        if side == 'sell':
                            df_sorted.loc[idx, 'order_side'] = 'Open Sell'
                        else:
                            df_sorted.loc[idx, 'order_side'] = 'Close Buy'
                
                df = df_sorted
                logger.info("Pattern-based classification applied")
                logger.info("Updated order classification breakdown:")
                logger.info(f"  Open Buy: {len(df[df['order_side'] == 'Open Buy'])}")
                logger.info(f"  Close Sell: {len(df[df['order_side'] == 'Close Sell'])}")
                logger.info(f"  Open Sell: {len(df[df['order_side'] == 'Open Sell'])}")
                logger.info(f"  Close Buy: {len(df[df['order_side'] == 'Close Buy'])}")
        
        # Save processed orders to CSV
        save_processed_orders_to_csv(df, "processed_orders_data.csv")
        
        trades = []
        processed_indices = set()
        
        # Pair Open Buy with Close Sell
        open_buys = df[df['order_side'] == 'Open Buy'].copy()
        close_sells = df[df['order_side'] == 'Close Sell'].copy()
        
        logger.info(f"Pairing {len(open_buys)} Open Buys with {len(close_sells)} Close Sells")
        
        for _, open_buy in open_buys.iterrows():
            if open_buy.name in processed_indices:
                continue
            
            open_buy_time = open_buy['created_at']
            
            # Find unprocessed Close Sells that come after this Open Buy
            future_close_sells = close_sells[
                (close_sells['created_at'] > open_buy_time) & 
                (~close_sells.index.isin(processed_indices))
            ]
            
            if not future_close_sells.empty:
                # Find the closest Close Sell in time (within 24 hours)
                time_diff = (future_close_sells['created_at'] - open_buy_time).abs()
                valid_matches = future_close_sells[time_diff <= pd.Timedelta(hours=24)]
                
                if not valid_matches.empty:
                    # Take the closest match
                    closest_idx = time_diff.idxmin()
                    close_sell = close_sells.loc[closest_idx]
                    
                    # ENSURE: Exit datetime > Entry datetime
                    if close_sell['created_at'] <= open_buy_time:
                        logger.warning(f"Skipping invalid pair: Exit time {close_sell['created_at']} <= Entry time {open_buy_time}")
                        continue
                    
                    # Calculate trade metrics with validation
                    try:
                        entry_qty = float(open_buy['size'])
                        exit_qty = float(close_sell['size'])
                        trade_qty = min(entry_qty, exit_qty)
                        
                        if trade_qty <= 0:
                            logger.warning(f"Skipping trade with invalid quantity: {trade_qty}")
                            continue
                        
                        entry_price = float(open_buy['average_fill_price'])
                        exit_price = float(close_sell['average_fill_price'])
                        
                        if entry_price <= 0 or exit_price <= 0:
                            logger.warning(f"Skipping trade with invalid prices: entry={entry_price}, exit={exit_price}")
                            continue
                        
                        # Calculate cashflow (notional value)
                        entry_cashflow = entry_price * trade_qty
                        exit_cashflow = exit_price * trade_qty
                        net_cashflow = exit_cashflow - entry_cashflow
                        
                        # Calculate fees with validation
                        entry_fees = float(open_buy.get('paid_commission', 0))
                        exit_fees = float(close_sell.get('paid_commission', 0))
                        total_fees = entry_fees + exit_fees
                        
                        # Calculate P&L
                        pnl = net_cashflow - total_fees
                        
                        # Calculate duration
                        duration = (close_sell['created_at'] - open_buy['created_at']).total_seconds() / 3600
                        
                        trade = {
                            'Entry DateTime': convert_to_india_time(open_buy['created_at'].isoformat()),
                            'Exit DateTime': convert_to_india_time(close_sell['created_at'].isoformat()),
                            'Entry Order ID': open_buy['id'],
                            'Entry Side': open_buy['order_side'],
                            'Entry Price': round(entry_price, 2),
                            'Exit Order ID': close_sell['id'],
                            'Exit Side': close_sell['order_side'],
                            'Exit Price': round(exit_price, 2),
                            'Qty Traded': round(trade_qty, 2),
                            'Cashflow': round(net_cashflow, 2),
                            'Trading Fees': round(total_fees, 2),
                            'P&L': round(pnl, 2),
                            'Duration (hours)': round(duration, 2),
                            'Trade Status': 'Closed',
                            'Entry Timestamp': open_buy['created_at'],  # For sorting
                            'Exit Timestamp': close_sell['created_at']   # For sorting
                        }
                        
                        trades.append(trade)
                        
                        # Mark both orders as processed
                        processed_indices.add(open_buy.name)
                        processed_indices.add(closest_idx)
                        
                        logger.debug(f"Paired Long trade: Entry {open_buy['id']} -> Exit {close_sell['id']}, P&L: ${pnl:.2f}")
                        
                    except (ValueError, TypeError, KeyError) as e:
                        logger.error(f"Error calculating trade metrics: {e}")
                        continue
        
        # Pair Open Sell with Close Buy
        open_sells = df[df['order_side'] == 'Open Sell'].copy()
        close_buys = df[df['order_side'] == 'Close Buy'].copy()
        
        logger.info(f"Pairing {len(open_sells)} Open Sells with {len(close_buys)} Close Buys")
        
        for _, open_sell in open_sells.iterrows():
            if open_sell.name in processed_indices:
                continue
            
            open_sell_time = open_sell['created_at']
            
            # Find unprocessed Close Buys that come after this Open Sell
            future_close_buys = close_buys[
                (close_buys['created_at'] > open_sell_time) & 
                (~close_buys.index.isin(processed_indices))
            ]
            
            if not future_close_buys.empty:
                # Find the closest Close Buy in time (within 24 hours)
                time_diff = (future_close_buys['created_at'] - open_sell_time).abs()
                valid_matches = future_close_buys[time_diff <= pd.Timedelta(hours=24)]
                
                if not valid_matches.empty:
                    # Take the closest match
                    closest_idx = time_diff.idxmin()
                    close_buy = close_buys.loc[closest_idx]
                    
                    # ENSURE: Exit datetime > Entry datetime
                    if close_buy['created_at'] <= open_sell_time:
                        logger.warning(f"Skipping invalid pair: Exit time {close_buy['created_at']} <= Entry time {open_sell_time}")
                        continue
                    
                    # Calculate trade metrics with validation
                    try:
                        entry_qty = float(open_sell['size'])
                        exit_qty = float(close_buy['size'])
                        trade_qty = min(entry_qty, exit_qty)
                        
                        if trade_qty <= 0:
                            logger.warning(f"Skipping trade with invalid quantity: {trade_qty}")
                            continue
                        
                        entry_price = float(open_sell['average_fill_price'])
                        exit_price = float(close_buy['average_fill_price'])
                        
                        if entry_price <= 0 or exit_price <= 0:
                            logger.warning(f"Skipping trade with invalid prices: entry={entry_price}, exit={exit_price}")
                            continue
                        
                        # Calculate cashflow (notional value)
                        entry_cashflow = entry_price * trade_qty
                        exit_cashflow = exit_price * trade_qty
                        net_cashflow = entry_cashflow - exit_cashflow  # For short trades
                        
                        # Calculate fees with validation
                        entry_fees = float(open_sell.get('paid_commission', 0))
                        exit_fees = float(close_buy.get('paid_commission', 0))
                        total_fees = entry_fees + exit_fees
                        
                        # Calculate P&L
                        pnl = net_cashflow - total_fees
                        
                        # Calculate duration
                        duration = (close_buy['created_at'] - open_sell['created_at']).total_seconds() / 3600
                        
                        trade = {
                            'Entry DateTime': convert_to_india_time(open_sell['created_at'].isoformat()),
                            'Exit DateTime': convert_to_india_time(close_buy['created_at'].isoformat()),
                            'Entry Order ID': open_sell['id'],
                            'Entry Side': open_sell['order_side'],
                            'Entry Price': round(entry_price, 2),
                            'Exit Order ID': close_buy['id'],
                            'Exit Side': close_buy['order_side'],
                            'Exit Price': round(exit_price, 2),
                            'Qty Traded': round(trade_qty, 2),
                            'Cashflow': round(net_cashflow, 2),
                            'Trading Fees': round(total_fees, 2),
                            'P&L': round(pnl, 2),
                            'Duration (hours)': round(duration, 2),
                            'Trade Status': 'Closed',
                            'Entry Timestamp': open_sell['created_at'],  # For sorting
                            'Exit Timestamp': close_buy['created_at']    # For sorting
                        }
                        
                        trades.append(trade)
                        
                        # Mark both orders as processed
                        processed_indices.add(open_sell.name)
                        processed_indices.add(closest_idx)
                        
                        logger.debug(f"Paired Short trade: Entry {open_sell['id']} -> Exit {close_buy['id']}, P&L: ${pnl:.2f}")
                        
                    except (ValueError, TypeError, KeyError) as e:
                        logger.error(f"Error calculating trade metrics: {e}")
                        continue
        
        # Handle unpaired entry orders (open positions)
        unpaired_entries = df[
            (df['order_side'].isin(['Open Buy', 'Open Sell'])) & 
            (~df.index.isin(processed_indices))
        ]
        
        logger.info(f"Found {len(unpaired_entries)} unpaired entry orders (open positions)")
        
        for _, entry_order in unpaired_entries.iterrows():
            try:
                entry_price = float(entry_order['average_fill_price'])
                entry_qty = float(entry_order['size'])
                
                if entry_price <= 0 or entry_qty <= 0:
                    logger.warning(f"Skipping open position with invalid data: price={entry_price}, qty={entry_qty}")
                    continue
                
                trade = {
                    'Entry DateTime': convert_to_india_time(entry_order['created_at'].isoformat()),
                    'Exit DateTime': '',  # Blank for open positions
                    'Entry Order ID': entry_order['id'],
                    'Entry Side': entry_order['order_side'],
                    'Entry Price': round(entry_price, 2),
                    'Exit Order ID': '',  # Blank for open positions
                    'Exit Side': '',  # Blank for open positions
                    'Exit Price': '',  # Blank for open positions
                    'Qty Traded': round(entry_qty, 2),
                    'Cashflow': '',  # Blank for open positions
                    'Trading Fees': round(float(entry_order.get('paid_commission', 0)), 2),
                    'P&L': '',  # Blank for open positions
                    'Duration (hours)': '',  # Blank for open positions
                    'Trade Status': 'Open',
                    'Entry Timestamp': entry_order['created_at'],  # For sorting
                    'Exit Timestamp': entry_order['created_at']    # For open positions, use entry time
                }
                
                trades.append(trade)
                logger.debug(f"Open position: Entry {entry_order['id']} ({entry_order['order_side']})")
                
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Error processing open position: {e}")
                continue
        
        if not trades:
            logger.warning("No trades found")
            return pd.DataFrame()
        
        # Create DataFrame and sort by entry timestamp to ensure chronological order
        trades_df = pd.DataFrame(trades)
        
        if trades_df.empty:
            logger.warning("No trades to process")
            return trades_df
        
        trades_df = trades_df.sort_values('Entry Timestamp').reset_index(drop=True)
        
        # ENSURE: Entry datetime of each trade > Exit datetime of previous trade (except first trade)
        valid_trades = []
        last_exit_time = None
        
        for idx, trade in trades_df.iterrows():
            try:
                entry_time = trade['Entry Timestamp']
                
                # For the first trade, no previous exit time to compare
                if idx == 0:
                    valid_trades.append(trade)
                    if trade['Trade Status'] == 'Closed':
                        last_exit_time = trade['Exit Timestamp']
                    else:
                        last_exit_time = entry_time  # For open positions
                    continue
                
                # For subsequent trades, ensure entry time > last exit time
                if last_exit_time is not None and entry_time <= last_exit_time:
                    logger.warning(f"Skipping trade {idx}: Entry time {entry_time} <= Previous exit time {last_exit_time}")
                    continue
                
                valid_trades.append(trade)
                if trade['Trade Status'] == 'Closed':
                    last_exit_time = trade['Exit Timestamp']
                else:
                    last_exit_time = entry_time  # For open positions
                    
            except Exception as e:
                logger.error(f"Error processing trade {idx}: {e}")
                continue
        
        # Create final DataFrame with valid trades
        final_trades_df = pd.DataFrame(valid_trades)
        
        if final_trades_df.empty:
            logger.warning("No valid trades after chronological filtering")
            return final_trades_df
        
        # Remove temporary timestamp columns used for sorting
        if 'Entry Timestamp' in final_trades_df.columns:
            final_trades_df = final_trades_df.drop(['Entry Timestamp', 'Exit Timestamp'], axis=1)
        
        # Calculate statistics
        closed_trades = final_trades_df[final_trades_df['Trade Status'] == 'Closed']
        open_positions = final_trades_df[final_trades_df['Trade Status'] == 'Open']
        
        logger.info(f"Trade Summary:")
        logger.info(f"  Total trades: {len(final_trades_df)}")
        logger.info(f"  Closed trades: {len(closed_trades)}")
        logger.info(f"  Open positions: {len(open_positions)}")
        
        if not closed_trades.empty:
            total_pnl = closed_trades['P&L'].sum()
            total_fees = closed_trades['Trading Fees'].sum()
            winning_trades = len(closed_trades[closed_trades['P&L'] > 0])
            win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0
            
            logger.info(f"  Total P&L: ${total_pnl:.2f}")
            logger.info(f"  Total fees: ${total_fees:.2f}")
            logger.info(f"  Win rate: {win_rate:.1f}%")
        
        return final_trades_df
        
    except Exception as e:
        logger.error(f"Error pairing trades: {e}")
        return pd.DataFrame()

def save_processed_orders_to_csv(df, filename="processed_orders_data.csv"):
    """
    Save processed orders DataFrame to CSV after classification
    
    Args:
        df (pd.DataFrame): Processed orders DataFrame
        filename (str): Output filename
    """
    try:
        if df is None or df.empty:
            logger.warning("No processed orders to save")
            return
        
        # Save to CSV
        df.to_csv(filename, index=False)
        logger.info(f"Processed orders data saved to: {filename}")
        logger.info(f"Processed data shape: {df.shape}")
        
        # Log classification summary
        if 'order_side' in df.columns:
            logger.info("Order classification summary:")
            classification_counts = df['order_side'].value_counts()
            for side, count in classification_counts.items():
                logger.info(f"  {side}: {count}")
        
    except Exception as e:
        logger.error(f"Error saving processed orders to CSV: {e}")

def save_raw_orders_to_csv(orders, filename="raw_orders_data.csv"):
    """
    Save raw orders data to CSV for analysis and debugging
    
    Args:
        orders (list): List of order dictionaries
        filename (str): Output filename
    """
    try:
        if not orders:
            logger.warning("No orders to save")
            return
        
        df = pd.DataFrame(orders)
        
        # Save to CSV
        df.to_csv(filename, index=False)
        logger.info(f"Raw orders data saved to: {filename}")
        logger.info(f"Raw data shape: {df.shape}")
        logger.info(f"Raw data columns: {list(df.columns)}")
        
        # Log sample data
        if not df.empty:
            logger.info("Sample raw order data:")
            sample_row = df.iloc[0]
            for col in df.columns:
                try:
                    value = sample_row[col]
                    # Truncate long values for logging
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"  {col}: {value}")
                except Exception as e:
                    logger.warning(f"Error logging column {col}: {e}")
        
    except Exception as e:
        logger.error(f"Error saving raw orders to CSV: {e}")

def save_trades_to_csv(trades_df, filename="delta_trades_report.csv"):
    """
    Save trades DataFrame to CSV with proper formatting
    
    Args:
        trades_df (pd.DataFrame): Trades DataFrame
        filename (str): Output filename
    """
    try:
        if trades_df is None or trades_df.empty:
            logger.warning("No trades to save")
            return
        
        # Ensure numeric columns are properly formatted
        numeric_columns = ['Entry Price', 'Exit Price', 'Qty Traded', 'Cashflow', 'Trading Fees', 'P&L', 'Duration (hours)']
        for col in numeric_columns:
            if col in trades_df.columns:
                try:
                    # Convert to numeric, handling empty strings
                    trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                    # Round to 2 decimal places
                    trades_df[col] = trades_df[col].round(2)
                except Exception as e:
                    logger.warning(f"Error formatting column {col}: {e}")
        
        # Save to CSV
        trades_df.to_csv(filename, index=False, float_format='%.2f')
        logger.info(f"Trades report saved to: {filename}")
        
        # Log sample data
        if not trades_df.empty:
            logger.info("Sample trade data:")
            sample_row = trades_df.iloc[0]
            for col in trades_df.columns:
                try:
                    logger.info(f"  {col}: {sample_row[col]}")
                except Exception as e:
                    logger.warning(f"Error logging column {col}: {e}")
        
    except Exception as e:
        logger.error(f"Error saving trades to CSV: {e}")
        # Try to save without formatting
        try:
            trades_df.to_csv(filename, index=False)
            logger.info(f"Trades report saved to: {filename} (without formatting)")
        except Exception as e2:
            logger.error(f"Failed to save trades even without formatting: {e2}")

def main():
    """Main function to generate Delta Exchange trading report"""
    try:
        logger.info("Starting Delta Exchange trading report generation...")
        
        # Get all closed orders
        orders = get_all_closed_orders(product_id=SYMBOL_ID)
        
        if not orders:
            logger.error("No orders found")
            return
        
        logger.info(f"Processing {len(orders)} orders...")
        
        # Save raw orders to CSV
        save_raw_orders_to_csv(orders, "raw_orders_data.csv")

        # Pair trades
        trades_df = pair_trades(orders)
        
        if not trades_df.empty:
            # Save to CSV with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            trades_filename = f"delta_trades_report_{timestamp}.csv"
            save_trades_to_csv(trades_df, trades_filename)
            
            # Also save without timestamp for easy access
            save_trades_to_csv(trades_df, "delta_trades_report.csv")
            
            # Print summary
            print(f"\n=== Delta Exchange Trading Report ===")
            print(f"Total trades: {len(trades_df)}")
            
            closed_trades = trades_df[trades_df['Trade Status'] == 'Closed']
            open_positions = trades_df[trades_df['Trade Status'] == 'Open']
            
            print(f"Closed trades: {len(closed_trades)}")
            print(f"Open positions: {len(open_positions)}")
            
            if not closed_trades.empty:
                total_pnl = closed_trades['P&L'].sum()
                total_fees = closed_trades['Trading Fees'].sum()
                winning_trades = len(closed_trades[closed_trades['P&L'] > 0])
                win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0
                
                print(f"Total P&L: ${total_pnl:.2f}")
                print(f"Total fees: ${total_fees:.2f}")
                print(f"Win rate: {win_rate:.1f}%")
            
            print(f"\nReports saved to:")
            print(f"  - {trades_filename} (timestamped)")
            print(f"  - delta_trades_report.csv (latest)")
            print(f"  - raw_orders_data.csv (raw API data)")
            print(f"  - processed_orders_data.csv (classified orders)")
        else:
            print("No trades found")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 