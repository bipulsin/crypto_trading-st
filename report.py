import pandas as pd
import requests
import time
import hashlib
import hmac
import json
import os
from datetime import datetime
from config import API_KEY, API_SECRET, BASE_URL, SYMBOL_ID, LEVERAGE
from logger import get_logger
import io

# Set up logger
logger = get_logger('report', 'logs/report.log')

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

def download_fills_history_csv(start_time=None, end_time=None, product_id=None):
    """
    Download fills history as CSV from Delta exchange
    
    Args:
        start_time (int, optional): Start time in milliseconds since epoch
        end_time (int, optional): End time in milliseconds since epoch  
        product_id (int, optional): Product ID to filter by. If None, uses SYMBOL_ID from config
        
    Returns:
        str: CSV content as string, or None if failed
    """
    if product_id is None:
        product_id = SYMBOL_ID
    
    try:
        path = "/v2/fills/history/download/csv"
        params = {"product_id": product_id}
        
        # Try different parameter formats
        if start_time is not None:
            # Try both start_time and start parameters
            params["start_time"] = start_time
            params["start"] = start_time
        if end_time is not None:
            # Try both end_time and end parameters
            params["end_time"] = end_time
            params["end"] = end_time
        
        # Build the query string for signing
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        path_with_params = f"{path}?{query_string}"
        
        logger.info(f"API Call: {BASE_URL}{path_with_params}")
        logger.info(f"Parameters: {params}")
        
        headers, timestamp, message, signature = sign_request("GET", path_with_params)
        
        session = requests.Session()
        r = session.get(BASE_URL + path_with_params, headers=headers, timeout=30)
        
        logger.info(f"Response status: {r.status_code}")
        logger.info(f"Response headers: {dict(r.headers)}")
        
        if r.status_code != 200:
            logger.error(f"API Error: {r.status_code} - {r.text}")
            return None
        
        # Check if response is CSV
        content_type = r.headers.get('content-type', '')
        logger.info(f"Content-Type: {content_type}")
        
        if 'text/csv' in content_type or 'application/octet-stream' in content_type or 'text/plain' in content_type:
            content = r.text
            logger.info(f"Received content length: {len(content)}")
            
            # Check if content has data rows (more than just header)
            lines = content.strip().split('\n')
            if len(lines) <= 1:
                logger.warning("CSV contains only header, no data rows")
                return None
                
            return content
        else:
            # Try to parse as JSON to get error message
            try:
                data = r.json()
                logger.error(f"API returned JSON instead of CSV: {data}")
                if not data.get('success'):
                    raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            except:
                pass
            raise Exception(f"Response is not CSV format. Content-Type: {content_type}")
            
    except Exception as e:
        logger.error(f"Error downloading fills history CSV: {e}")
        return None

def determine_order_side(row):
    """
    Determine if a fill is opening or closing a position
    
    Args:
        row: DataFrame row with fill data
        
    Returns:
        str: 'Open Buy', 'Close Sell', 'Open Sell', 'Close Buy'
    """
    side = row['Side']
    order_price = float(row['Order Price'])
    exec_price = float(row['Exec.Price'])
    order_type = row['Order Type']
    
    # For market orders, use Order Price to determine if opening or closing
    if order_type == 'market_order':
        if side == 'buy':
            # Buy with high order price = opening position
            if order_price > 1000:  # Realistic price for BTC
                return 'Open Buy'
            else:
                return 'Close Buy'
        else:  # sell
            # Sell with low order price = closing position
            if order_price < 100:  # Low price indicates closing
                return 'Close Sell'
            else:
                return 'Open Sell'
    
    # For limit orders, assume they are opening positions
    # (since limit orders are typically used to open positions)
    elif order_type == 'limit_order':
        if side == 'buy':
            return 'Open Buy'
        else:
            return 'Open Sell'
    
    # Default fallback
    else:
        if side == 'buy':
            return 'Open Buy'
        else:
            return 'Open Sell'

def process_fills_to_trades(df):
    """
    Process fills dataframe into trades dataframe
    
    Args:
        df (pd.DataFrame): Raw fills dataframe
        
    Returns:
        pd.DataFrame: Processed trades dataframe
    """
    try:
        # Ensure required columns exist
        required_columns = ['Time', 'Side', 'Filled Qty', 'Value', 'Fees paid', 'Order Price', 'Order Type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")
            return pd.DataFrame()
        
        # Parse datetime
        df['Time'] = pd.to_datetime(df['Time'].str.split('+').str[0], errors='coerce')
        
        # Add order side classification
        df['Order Side'] = df.apply(determine_order_side, axis=1)
        
        # Sort by time
        df = df.sort_values('Time').reset_index(drop=True)
        
        # Filter out rows with NaT in Time column
        df = df.dropna(subset=['Time'])
        
        if df.empty:
            logger.warning("No valid fills data after filtering")
            return df
        
        logger.info(f"Processing {len(df)} fills records")
        logger.info(f"Order sides breakdown:")
        logger.info(f"  Open Buy: {len(df[df['Order Side'] == 'Open Buy'])}")
        logger.info(f"  Close Sell: {len(df[df['Order Side'] == 'Close Sell'])}")
        logger.info(f"  Open Sell: {len(df[df['Order Side'] == 'Open Sell'])}")
        logger.info(f"  Close Buy: {len(df[df['Order Side'] == 'Close Buy'])}")
        
        # Improved trade pairing logic based on order sides
        trades = []
        processed_indices = set()
        
        # Sort all fills by time for sequential processing
        all_fills = df.sort_values('Time').reset_index(drop=True)
        
        # First, collect all Open Buy and Close Sell pairs
        open_buys = all_fills[all_fills['Order Side'] == 'Open Buy'].copy()
        close_sells = all_fills[all_fills['Order Side'] == 'Close Sell'].copy()
        
        # Create a matrix of time differences between all Open Buy and Close Sell pairs
        if not open_buys.empty and not close_sells.empty:
            logger.info(f"Finding optimal matches between {len(open_buys)} Open Buys and {len(close_sells)} Close Sells")
            
            # For each Open Buy, find the best Close Sell match
            for _, open_buy in open_buys.iterrows():
                if open_buy.name in processed_indices:
                    continue
                
                open_buy_time = open_buy['Time']
                open_buy_id = open_buy.get('Order ID', '')
                
                # Find all Close Sells that come after this Open Buy and are not processed
                future_close_sells = close_sells[
                    (close_sells['Time'] > open_buy_time) & 
                    (~close_sells.index.isin(processed_indices))
                ]
                
                if not future_close_sells.empty:
                    # Find the closest Close Sell in time (within 24 hours)
                    time_diff = (future_close_sells['Time'] - open_buy_time).abs()
                    valid_matches = future_close_sells[time_diff <= pd.Timedelta(hours=24)]
                    
                    if not valid_matches.empty:
                        # Take the closest match
                        closest_idx = time_diff.idxmin()
                        close_sell = close_sells.loc[closest_idx]
                        close_sell_id = close_sell.get('Order ID', '')
                        
                        # Debug: Check specific order IDs
                        if open_buy_id in [663612723, 663612729] or close_sell_id in [663612723, 663612729]:
                            logger.info(f"  Matched: {open_buy_id} (Open Buy) -> {close_sell_id} (Close Sell)")
                        
                        # Calculate trade metrics
                        entry_qty = float(open_buy['Filled Qty'])
                        exit_qty = float(close_sell['Filled Qty'])
                        
                        # Use the smaller quantity to ensure complete trade
                        trade_qty = min(entry_qty, exit_qty)
                        
                        # Calculate proportional values
                        entry_cashflow = float(open_buy['Value']) * (trade_qty / float(open_buy['Filled Qty']))
                        exit_cashflow = float(close_sell['Value']) * (trade_qty / float(close_sell['Filled Qty']))
                        
                        entry_fees = float(open_buy['Fees paid']) * (trade_qty / float(open_buy['Filled Qty']))
                        exit_fees = float(close_sell['Fees paid']) * (trade_qty / float(close_sell['Filled Qty']))
                        
                        # Calculate net cashflow and fees
                        net_cashflow = exit_cashflow - entry_cashflow
                        total_fees = entry_fees + exit_fees
                        
                        # Calculate P&L
                        pnl = net_cashflow - total_fees
                        
                        trade = {
                            'Entry Time': open_buy['Time'],
                            'Exit Time': close_sell['Time'],
                            'Entry ID': open_buy.get('Order ID', ''),
                            'Exit ID': close_sell.get('Order ID', ''),
                            'Entry Side': open_buy['Order Side'],
                            'Exit Side': close_sell['Order Side'],
                            'Side': 'Long',
                            'Quantity': trade_qty,
                            'Entry Price': entry_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Exit Price': exit_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Cashflow': net_cashflow,
                            'Trading Fees': total_fees,
                            'Realised P&L': pnl,
                            'Duration': (close_sell['Time'] - open_buy['Time']).total_seconds() / 3600  # hours
                        }
                        
                        trades.append(trade)
                        
                        # Mark both fills as processed
                        processed_indices.add(open_buy.name)
                        processed_indices.add(closest_idx)
                        
                        logger.debug(f"Matched trade: Long {trade_qty} contracts, Entry: {open_buy.get('Order ID')} (Open Buy), Exit: {close_sell.get('Order ID')} (Close Sell), P&L: ${pnl:.2f}")
        
        # Now handle Open Sell and Close Buy pairs (if any)
        open_sells = all_fills[all_fills['Order Side'] == 'Open Sell'].copy()
        close_buys = all_fills[all_fills['Order Side'] == 'Close Buy'].copy()
        
        if not open_sells.empty and not close_buys.empty:
            logger.info(f"Finding optimal matches between {len(open_sells)} Open Sells and {len(close_buys)} Close Buys")
            
            # For each Open Sell, find the best Close Buy match
            for _, open_sell in open_sells.iterrows():
                if open_sell.name in processed_indices:
                    continue
                
                open_sell_time = open_sell['Time']
                open_sell_id = open_sell.get('Order ID', '')
                
                # Find all Close Buys that come after this Open Sell and are not processed
                future_close_buys = close_buys[
                    (close_buys['Time'] > open_sell_time) & 
                    (~close_buys.index.isin(processed_indices))
                ]
                
                if not future_close_buys.empty:
                    # Find the closest Close Buy in time (within 24 hours)
                    time_diff = (future_close_buys['Time'] - open_sell_time).abs()
                    valid_matches = future_close_buys[time_diff <= pd.Timedelta(hours=24)]
                    
                    if not valid_matches.empty:
                        # Take the closest match
                        closest_idx = time_diff.idxmin()
                        close_buy = close_buys.loc[closest_idx]
                        close_buy_id = close_buy.get('Order ID', '')
                        
                        # Calculate trade metrics
                        entry_qty = float(open_sell['Filled Qty'])
                        exit_qty = float(close_buy['Filled Qty'])
                        
                        # Use the smaller quantity to ensure complete trade
                        trade_qty = min(entry_qty, exit_qty)
                        
                        # Calculate proportional values
                        entry_cashflow = float(open_sell['Value']) * (trade_qty / float(open_sell['Filled Qty']))
                        exit_cashflow = float(close_buy['Value']) * (trade_qty / float(close_buy['Filled Qty']))
                        
                        entry_fees = float(open_sell['Fees paid']) * (trade_qty / float(open_sell['Filled Qty']))
                        exit_fees = float(close_buy['Fees paid']) * (trade_qty / float(close_buy['Filled Qty']))
                        
                        # Calculate net cashflow and fees
                        net_cashflow = entry_cashflow - exit_cashflow
                        total_fees = entry_fees + exit_fees
                        
                        # Calculate P&L
                        pnl = net_cashflow - total_fees
                        
                        trade = {
                            'Entry Time': open_sell['Time'],
                            'Exit Time': close_buy['Time'],
                            'Entry ID': open_sell.get('Order ID', ''),
                            'Exit ID': close_buy.get('Order ID', ''),
                            'Entry Side': open_sell['Order Side'],
                            'Exit Side': close_buy['Order Side'],
                            'Side': 'Short',
                            'Quantity': trade_qty,
                            'Entry Price': entry_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Exit Price': exit_cashflow / trade_qty if trade_qty > 0 else 0,
                            'Cashflow': net_cashflow,
                            'Trading Fees': total_fees,
                            'Realised P&L': pnl,
                            'Duration': (close_buy['Time'] - open_sell['Time']).total_seconds() / 3600  # hours
                        }
                        
                        trades.append(trade)
                        
                        # Mark both fills as processed
                        processed_indices.add(open_sell.name)
                        processed_indices.add(closest_idx)
                        
                        logger.debug(f"Matched trade: Short {trade_qty} contracts, Entry: {open_sell.get('Order ID')} (Open Sell), Exit: {close_buy.get('Order ID')} (Close Buy), P&L: ${pnl:.2f}")
        
        if not trades:
            logger.warning("No complete trades found")
            return pd.DataFrame()
        
        trades_df = pd.DataFrame(trades)
        
        # Calculate statistics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['Realised P&L'] > 0])
        losing_trades = len(trades_df[trades_df['Realised P&L'] < 0])
        
        total_pnl = trades_df['Realised P&L'].sum()
        total_fees = trades_df['Trading Fees'].sum()
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        logger.info(f"Processed {total_trades} trades:")
        logger.info(f"  Winning trades: {winning_trades} ({win_rate:.1f}%)")
        logger.info(f"  Losing trades: {losing_trades}")
        logger.info(f"  Total P&L: ${total_pnl:.2f}")
        logger.info(f"  Total fees: ${total_fees:.2f}")
        
        # Show sample trades
        if not trades_df.empty:
            logger.info("Sample trades:")
            sample_trades = trades_df.head(3)
            for _, trade in sample_trades.iterrows():
                logger.info(f"  {trade['Side']}: Entry {trade['Entry ID']} ({trade['Entry Side']}) -> Exit {trade['Exit ID']} ({trade['Exit Side']}), P&L: ${trade['Realised P&L']:.2f}")
        
        return trades_df
        
    except Exception as e:
        logger.error(f"Error processing fills to trades: {e}")
        return pd.DataFrame()

def download_and_process_trades():
    """Download fills history CSV from Delta exchange and process it"""
    
    try:
        # Download fills history without time parameters (this works)
        logger.info("Downloading fills history...")
        csv_content = download_fills_history_csv(product_id=SYMBOL_ID)
        
        if not csv_content or len(csv_content.strip()) <= 200:
            logger.error("No fills data found")
            return pd.DataFrame()
        
        # Store the downloaded CSV content
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fills_filename = f'fills_history_{timestamp}.csv'
        
        # Save the raw fills history CSV
        with open(fills_filename, 'w') as f:
            f.write(csv_content)
        
        logger.info(f"Downloaded fills history saved to: {fills_filename}")
        
        # Parse CSV content
        df = pd.read_csv(io.StringIO(csv_content))
        
        if df.empty:
            logger.warning("No fills data found after parsing")
            return df
        
        logger.info(f"Processing {len(df)} fills records")
        
        # Process the fills into trades
        trades_df = process_fills_to_trades(df)
        
        if not trades_df.empty:
            # Save processed trades to CSV
            filename = 'trades_report.csv'
            trades_df.to_csv(filename, index=False)
            logger.info(f"Trades report saved to: {filename}")
        
        return trades_df
        
    except Exception as e:
        logger.error(f"Error processing trades from fills history: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    result = download_and_process_trades()
    if not result.empty:
        print(f"\nReport Summary:")
        print(f"Total trades: {len(result)}")
        print(f"Total P&L: ${result['Realised P&L'].sum():.2f}")
        print(f"Win rate: {(len(result[result['Realised P&L'] > 0]) / len(result) * 100):.1f}%")
    else:
        print("No trade data available")
