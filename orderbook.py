#!/usr/bin/env python3
"""
Trades Downloader for Delta Exchange India

This script downloads all closed orders from Delta Exchange India using the
GET /v2/orders/history API, pairs them into complete trades, and saves them to a CSV file.
"""

import requests
import pandas as pd
import json
import time
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
import os
from config import API_KEY, API_SECRET, BASE_URL

def sign_request(method, path, body=None):
    """
    Sign the request using HMAC SHA256
    
    Args:
        method (str): HTTP method (GET, POST, etc.)
        path (str): API path
        body (str, optional): Request body
        
    Returns:
        tuple: (headers, timestamp, message, signature)
    """
    # Use current time in seconds (not milliseconds)
    timestamp = str(int(time.time()))
    
    # Format: method + timestamp + path + body
    message = method + timestamp + path
    
    if body:
        message += body
    
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'api-key': API_KEY,
        'timestamp': timestamp,
        'signature': signature,
        'Content-Type': 'application/json'
    }
    
    return headers, timestamp, message, signature

def get_closed_orders(limit=100, offset=0, product_id=None):
    """
    Get closed orders from Delta Exchange India
    
    Args:
        limit (int): Number of orders to fetch (max 100)
        offset (int): Offset for pagination
        product_id (int, optional): Filter by product ID
        
    Returns:
        dict: Orders data or None if failed
    """
    try:
        path = "/v2/orders/history"
        params = {
            "limit": limit,
            "offset": offset,
            "state": "closed"  # Only get closed orders
        }
        
        if product_id:
            params["product_id"] = product_id
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        path_with_params = f"{path}?{query_string}"
        
        print(f"Fetching closed orders...")
        print(f"API Call: {BASE_URL}{path_with_params}")
        print(f"Parameters: {params}")
        
        headers, timestamp, message, signature = sign_request("GET", path_with_params)
        
        session = requests.Session()
        r = session.get(BASE_URL + path_with_params, headers=headers, timeout=30)
        
        print(f"Response status: {r.status_code}")
        
        if r.status_code != 200:
            print(f"API Error: {r.status_code} - {r.text}")
            return None
        
        data = r.json()
        
        if not data.get('success'):
            print(f"API returned error: {data.get('message', 'Unknown error')}")
            return None
        
        return data.get('result', {})
        
    except Exception as e:
        print(f"Error fetching closed orders: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_all_closed_orders(product_id=None, max_orders=1000, start_date=None):
    """
    Get all closed orders using pagination
    
    Args:
        product_id (int, optional): Filter by product ID
        max_orders (int): Maximum number of orders to fetch
        start_date (str, optional): Start date in YYYY-MM-DD format
        
    Returns:
        list: List of all closed orders
    """
    all_orders = []
    offset = 0
    limit = 100  # API limit per request
    
    print(f"Fetching all closed orders (max: {max_orders})...")
    
    while len(all_orders) < max_orders:
        print(f"Fetching orders {offset} to {offset + limit}...")
        
        orders_data = get_closed_orders(limit=limit, offset=offset, product_id=product_id)
        
        if orders_data is None:
            print("Failed to fetch orders data")
            break
        
        # The API returns orders directly in the 'result' field
        if isinstance(orders_data, dict):
            orders = orders_data.get('result', [])
        else:
            # If orders_data is already a list, use it directly
            orders = orders_data if isinstance(orders_data, list) else []
        
        if not orders:
            print("No more orders to fetch")
            break
        
        all_orders.extend(orders)
        print(f"Fetched {len(orders)} orders (total: {len(all_orders)})")
        
        # If we got fewer orders than requested, we've reached the end
        if len(orders) < limit:
            print("Reached end of orders")
            break
        
        offset += limit
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print(f"Total orders fetched: {len(all_orders)}")
    
    # Filter by start date if specified
    if start_date and all_orders:
        print(f"Filtering orders from {start_date} onwards...")
        start_timestamp = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        filtered_orders = []
        for order in all_orders:
            order_time = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
            if order_time >= start_timestamp:
                filtered_orders.append(order)
        
        print(f"After date filtering: {len(filtered_orders)} orders")
        return filtered_orders
    
    return all_orders

def convert_to_india_time(utc_time_str):
    """
    Convert UTC time string to India time (IST)
    
    Args:
        utc_time_str (str): UTC time string
        
    Returns:
        str: India time string
    """
    try:
        # Parse UTC time
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # Convert to India time (IST = UTC+5:30)
        india_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
        
        # Format as DD-MM-YYYY HH:MM:SS
        return india_time.strftime('%d-%m-%Y %H:%M:%S')
    except Exception as e:
        print(f"Error converting time: {e}")
        return utc_time_str

def determine_order_type(order):
    """
    Determine if an order is an entry or exit order
    
    Args:
        order (dict): Order data
        
    Returns:
        str: 'entry' or 'exit'
    """
    try:
        # Check if it's a reduce_only order (exit)
        if order.get('reduce_only', False):
            return 'exit'
        
        # Check if it's a bracket order (entry)
        if order.get('bracket_order', False):
            return 'entry'
        
        # Check meta_data for P&L information
        meta_data = order.get('meta_data', {})
        if 'pnl' in meta_data and meta_data['pnl'] != '0':
            return 'exit'
        
        # Check if it has entry/exit price information
        if 'entry_price' in meta_data:
            return 'exit'
        
        # Default logic based on side and order type
        side = order.get('side', '')
        order_type = order.get('order_type', '')
        
        # Market orders are typically entries
        if order_type == 'market_order' and not order.get('reduce_only', False):
            return 'entry'
        
        # Limit orders without reduce_only are typically entries
        if order_type == 'limit_order' and not order.get('reduce_only', False):
            return 'entry'
        
        return 'entry'  # Default to entry
        
    except Exception as e:
        print(f"Error determining order type: {e}")
        return 'entry'

def pair_trades(orders):
    """
    Pair entry and exit orders into complete trades
    
    Args:
        orders (list): List of order dictionaries
        
    Returns:
        list: List of paired trades
    """
    print(f"Pairing {len(orders)} orders into trades...")
    
    # Convert to DataFrame for easier processing
    df = pd.DataFrame(orders)
    
    # Filter out cancelled orders (those with None average_fill_price)
    df = df[df['average_fill_price'].notna()].copy()
    print(f"After filtering cancelled orders: {len(df)} orders")
    
    # Add order type classification
    df['order_type_class'] = df.apply(determine_order_type, axis=1)
    
    # Convert timestamps to datetime
    df['created_at_dt'] = pd.to_datetime(df['created_at'])
    df['updated_at_dt'] = pd.to_datetime(df['updated_at'])
    
    # Sort by creation time
    df = df.sort_values('created_at_dt')
    
    # Separate entry and exit orders
    entry_orders = df[df['order_type_class'] == 'entry'].copy()
    exit_orders = df[df['order_type_class'] == 'exit'].copy()
    
    print(f"Found {len(entry_orders)} entry orders and {len(exit_orders)} exit orders")
    
    # Debug: Show all orders with their classification
    print("\n=== Order Classification ===")
    for idx, row in df.iterrows():
        print(f"Order {row['id']}: {row['side']} {row['size']} @ {row.get('average_fill_price', row.get('limit_price', 'N/A'))} - {row['order_type_class']} - {row['created_at_dt']}")
    
    trades = []
    processed_exits = set()
    processed_entries = set()
    
    # Pair entry and exit orders
    for _, entry in entry_orders.iterrows():
        entry_time = entry['created_at_dt']
        entry_side = entry['side']
        
        print(f"\nLooking for exit for entry {entry['id']} ({entry_side} {entry['size']} @ {entry.get('average_fill_price', entry.get('limit_price', 'N/A'))})")
        
        # Find the closest exit order of opposite side that comes after this entry
        potential_exits = exit_orders[
            (exit_orders['side'] != entry_side) & 
            (exit_orders['created_at_dt'] > entry_time) &
            (~exit_orders.index.isin(processed_exits))
        ]
        
        print(f"Found {len(potential_exits)} potential exits")
        
        if not potential_exits.empty:
            # Find the closest exit in time
            time_diff = (potential_exits['created_at_dt'] - entry_time).abs()
            closest_exit_idx = time_diff.idxmin()
            exit_order = exit_orders.loc[closest_exit_idx]
            
            # Create trade record
            trade = {
                'trade_id': f"T{len(trades) + 1}",
                'entry_order_id': entry['id'],
                'exit_order_id': exit_order['id'],
                'entry_datetime': convert_to_india_time(entry['created_at']),
                'exit_datetime': convert_to_india_time(exit_order['created_at']),
                'entry_side': entry['side'],
                'exit_side': exit_order['side'],
                'qty_traded': entry['size'],
                'entry_price': entry.get('average_fill_price', entry.get('limit_price', 0)),
                'exit_price': exit_order.get('average_fill_price', exit_order.get('limit_price', 0)),
                'entry_fees': float(entry.get('paid_commission', 0)),
                'exit_fees': float(exit_order.get('paid_commission', 0)),
                'total_fees': float(entry.get('paid_commission', 0)) + float(exit_order.get('paid_commission', 0)),
                'entry_notional': float(entry.get('average_fill_price', entry.get('limit_price', 0))) * float(entry['size']),
                'exit_notional': float(exit_order.get('average_fill_price', exit_order.get('limit_price', 0))) * float(exit_order['size']),
                'cashflow': 0,  # Will calculate below
                'pnl': 0,  # Will calculate below
                'entry_order_type': entry['order_type'],
                'exit_order_type': exit_order['order_type'],
                'product_symbol': entry['product_symbol'],
                'user_id': entry['user_id']
            }
            
            # Calculate cashflow and P&L
            if entry['side'] == 'buy':
                # Long trade: exit_notional - entry_notional
                trade['cashflow'] = trade['exit_notional'] - trade['entry_notional']
                trade['pnl'] = trade['cashflow'] - trade['total_fees']
            else:
                # Short trade: entry_notional - exit_notional
                trade['cashflow'] = trade['entry_notional'] - trade['exit_notional']
                trade['pnl'] = trade['cashflow'] - trade['total_fees']
            
            trades.append(trade)
            processed_exits.add(closest_exit_idx)
            processed_entries.add(entry.name)
            
            print(f"Paired trade {trade['trade_id']}: {entry['side']} {entry['size']} @ {trade['entry_price']} -> {exit_order['side']} @ {trade['exit_price']}, P&L: ${trade['pnl']:.2f}")
        else:
            print(f"No suitable exit found for entry {entry['id']}")
    
    # Show unpaired orders
    print(f"\n=== Unpaired Orders ===")
    unpaired_entries = entry_orders[~entry_orders.index.isin(processed_entries)]
    unpaired_exits = exit_orders[~exit_orders.index.isin(processed_exits)]
    
    if not unpaired_entries.empty:
        print(f"Unpaired entry orders ({len(unpaired_entries)}):")
        for _, order in unpaired_entries.iterrows():
            print(f"  {order['id']}: {order['side']} {order['size']} @ {order.get('average_fill_price', order.get('limit_price', 'N/A'))} - {order['created_at_dt']}")
    
    if not unpaired_exits.empty:
        print(f"Unpaired exit orders ({len(unpaired_exits)}):")
        for _, order in unpaired_exits.iterrows():
            print(f"  {order['id']}: {order['side']} {order['size']} @ {order.get('average_fill_price', order.get('limit_price', 'N/A'))} - {order['created_at_dt']}")
    
    print(f"Successfully paired {len(trades)} trades")
    return trades

def save_trades_to_csv(trades, filename_prefix="trades"):
    """
    Save trades data to CSV file
    
    Args:
        trades (list): List of trade dictionaries
        filename_prefix (str): Prefix for the filename
        
    Returns:
        str: Filename of saved CSV
    """
    try:
        if not trades:
            print("No trades to save")
            return None
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{filename_prefix}_{timestamp}.csv'
        
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        # Reorder columns for better readability
        column_order = [
            'trade_id', 'entry_order_id', 'exit_order_id', 'entry_datetime', 'exit_datetime',
            'entry_side', 'exit_side', 'qty_traded', 'entry_price', 'exit_price',
            'entry_fees', 'exit_fees', 'total_fees', 'entry_notional', 'exit_notional',
            'cashflow', 'pnl', 'entry_order_type', 'exit_order_type', 'product_symbol', 'user_id'
        ]
        
        # Only include columns that exist
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Save to CSV
        df.to_csv(filename, index=False)
        print(f"Trades data saved to: {filename}")
        
        # Print summary
        print(f"\n=== Trades Summary ===")
        print(f"Total trades: {len(trades)}")
        
        if 'pnl' in df.columns:
            total_pnl = df['pnl'].sum()
            winning_trades = len(df[df['pnl'] > 0])
            losing_trades = len(df[df['pnl'] < 0])
            win_rate = (winning_trades / len(df)) * 100 if len(df) > 0 else 0
            
            print(f"Total P&L: ${total_pnl:.2f}")
            print(f"Winning trades: {winning_trades}")
            print(f"Losing trades: {losing_trades}")
            print(f"Win rate: {win_rate:.1f}%")
        
        if 'total_fees' in df.columns:
            total_fees = df['total_fees'].sum()
            print(f"Total fees: ${total_fees:.2f}")
        
        return filename
        
    except Exception as e:
        print(f"Error saving trades data: {e}")
        return None

def print_trades_summary(trades):
    """
    Print a detailed summary of the trades data
    
    Args:
        trades (list): List of trade dictionaries
    """
    try:
        if not trades:
            print("No trades data to summarize")
            return
        
        print(f"\n=== Detailed Trades Summary ===")
        print(f"Total trades: {len(trades)}")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(trades)
        
        # Side breakdown
        if 'entry_side' in df.columns:
            entry_sides = df['entry_side'].value_counts()
            print(f"Entry sides: {dict(entry_sides)}")
        
        # P&L analysis
        if 'pnl' in df.columns:
            total_pnl = df['pnl'].sum()
            avg_pnl = df['pnl'].mean()
            max_profit = df['pnl'].max()
            max_loss = df['pnl'].min()
            
            print(f"P&L Analysis:")
            print(f"  Total P&L: ${total_pnl:.2f}")
            print(f"  Average P&L: ${avg_pnl:.2f}")
            print(f"  Max Profit: ${max_profit:.2f}")
            print(f"  Max Loss: ${max_loss:.2f}")
            
            # Win rate
            winning_trades = len(df[df['pnl'] > 0])
            win_rate = (winning_trades / len(df)) * 100
            print(f"  Win Rate: {win_rate:.1f}%")
        
        # Sample trades
        print(f"\nSample trades:")
        for i, trade in enumerate(trades[:5]):
            print(f"  {trade['trade_id']}: {trade['entry_side']} {trade['qty_traded']} @ {trade['entry_price']} -> {trade['exit_side']} @ {trade['exit_price']}, P&L: ${trade['pnl']:.2f}")
        
    except Exception as e:
        print(f"Error printing summary: {e}")

def main():
    """
    Main function to download and process closed orders into trades
    """
    print(f"Delta Exchange India Trades Downloader")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 50)
    
    # Use testnet API (live API has IP restrictions)
    global BASE_URL, API_KEY, API_SECRET
    
    # Switch back to testnet API
    from config import BASE_URL as TESTNET_BASE_URL, API_KEY as TESTNET_API_KEY, API_SECRET as TESTNET_API_SECRET
    BASE_URL = TESTNET_BASE_URL
    API_KEY = TESTNET_API_KEY
    API_SECRET = TESTNET_API_SECRET
    
    print(f"Using Testnet API: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...")
    
    # Configuration
    product_id = None  # Set to specific product ID if needed (e.g., 84 for BTCUSD)
    max_orders = 5000  # Increased to fetch more historical data
    start_date = "2025-08-01" # Set the start date for August 1st, 2025
    
    # Get all closed orders
    orders_list = get_all_closed_orders(product_id=product_id, max_orders=max_orders, start_date=start_date)
    
    if not orders_list:
        print("No orders found")
        return
    
    # Pair orders into trades
    trades = pair_trades(orders_list)
    
    if not trades:
        print("No trades found")
        return
    
    # Print summary
    print_trades_summary(trades)
    
    # Save to CSV
    filename = save_trades_to_csv(trades)
    
    if filename:
        print(f"\nTrades successfully downloaded and saved!")
        print(f"File: {filename}")
    else:
        print("Failed to save trades data")

if __name__ == "__main__":
    main() 