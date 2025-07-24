import pandas as pd
import time
from delta_api import DeltaAPI

class LiveStrategy:
    def __init__(self, api=None):
        self.api = api if api else DeltaAPI()
        self.position = None  # 'LONG', 'SHORT', or None
        self.entry_price = None
        self.stop_loss = None
        self.payback_threshold = 1000
        self.payback_amount = 0
        self.last_payback = 0
        self.first_trade_done = False  # Track if first trade has been made
        self.cached_balance = None  # Cache for wallet balance
        self.balance_cache_time = 0  # Timestamp of last balance fetch
        self.balance_cache_duration = 60  # Cache balance for 60 seconds

    def get_cached_balance(self):
        """Get cached balance or fetch new one if cache expired"""
        current_time = time.time()
        if (self.cached_balance is None or 
            current_time - self.balance_cache_time > self.balance_cache_duration):
            self.cached_balance = self.api.get_balance()
            self.balance_cache_time = current_time
        return self.cached_balance

    def get_order_size(self, capital, price):
        # Use 100% of available capital with caching
        wallet_balance = self.get_cached_balance()
        leverage = 50
        if price > 0:
            order_size = int((0.5 * wallet_balance * leverage / price) * 1000)
        else:
            order_size = 10  # fallback to 10 lots if price fetch fails
        if order_size < 1:
            order_size = 1
        return order_size

    def check_payback(self, capital):
        if capital >= self.payback_threshold:
            return self.payback_amount
        return 0

    def calculate_stop_loss(self, entry_price, supertrend_price, position, order_size=None):
        """
        Calculate stop loss: either supertrend price or 10% reduction of total invested capital
        For LONG positions: stop loss is below entry price
        For SHORT positions: stop loss is above entry price
        
        Args:
            entry_price: Entry price for the position
            supertrend_price: SuperTrend price for the current candle
            position: 'LONG' or 'SHORT'
            order_size: Number of lots for the order (optional, for capital calculation)
        """
        if not pd.isna(supertrend_price) and supertrend_price > 0:
            # Use supertrend price if available
            return supertrend_price
        else:
            # Calculate total invested capital and use 10% reduction
            if order_size is not None:
                # Calculate total invested capital: order_size * entry_price * 0.001 (1 lot = 0.001 BTC)
                total_invested_capital = order_size * entry_price * 0.001
                # Calculate 10% of total invested capital
                capital_reduction = total_invested_capital * 0.10
                
                # Calculate stop loss price based on capital reduction
                if position == 'LONG':
                    # For LONG: stop loss = entry_price - (capital_reduction / (order_size * 0.001))
                    stop_loss_price = entry_price - (capital_reduction / (order_size * 0.001))
                    return stop_loss_price
                else:  # SHORT
                    # For SHORT: stop loss = entry_price + (capital_reduction / (order_size * 0.001))
                    stop_loss_price = entry_price + (capital_reduction / (order_size * 0.001))
                    return stop_loss_price
            else:
                # Fallback to 10% of entry price if order_size not provided
                if position == 'LONG':
                    return entry_price * 0.90  # 10% below entry price
                else:  # SHORT
                    return entry_price * 1.10  # 10% above entry price

    def decide(self, df, capital):
        # df: DataFrame with latest candles and supertrend_signal
        # Returns: action dict {action, side, qty, price, stop_loss, payback}
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        signal = last['supertrend_signal']
        prev_signal = prev['supertrend_signal']
        open_price = last['open']
        supertrend_price = last['supertrend']
        action = None
        payback = 0
        print("DEBUG: *** ",signal)
        
        # Calculate order size first so we can use it for stop loss calculation
        order_size = self.get_order_size(capital, open_price) if action else 0
        
        # First entry logic: take trade immediately based on current supertrend
        if not self.first_trade_done and self.position is None:
            if signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'LONG', order_size)
                self.first_trade_done = True
            elif signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'SHORT', order_size)
                self.first_trade_done = True
        # Entry/flip logic for subsequent trades
        elif self.position is None:
            if prev_signal == -1 and signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'LONG', order_size)
            elif prev_signal == 1 and signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'SHORT', order_size)
        elif self.position == 'LONG':
            if prev_signal == 1 and signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'SHORT', order_size)
            elif self.stop_loss is not None and last['low'] <= self.stop_loss:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'SHORT', order_size)
        elif self.position == 'SHORT':
            if prev_signal == -1 and signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'LONG', order_size)
            elif self.stop_loss is not None and last['high'] >= self.stop_loss:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = open_price
                order_size = self.get_order_size(capital, open_price)
                self.stop_loss = self.calculate_stop_loss(open_price, supertrend_price, 'LONG', order_size)
        # Payback logic
        payback = self.check_payback(capital)
        return {
            'action': action,
            'side': self.position,
            'qty': self.get_order_size(capital, open_price) if action else 0,
            'price': open_price,
            'stop_loss': self.stop_loss,
            'payback': payback
        }
