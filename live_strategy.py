import pandas as pd
import time
from delta_api import DeltaAPI
from config import LEVERAGE, POSITION_SIZE_PERCENT

class LiveStrategy:
    def __init__(self, api=None):
        self.api = api if api else DeltaAPI()
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.first_trade_done = False
        self.cached_balance = None
        self.balance_cache_time = 0
        self.balance_cache_duration = 60

    def get_cached_balance(self):
        current_time = time.time()
        if (self.cached_balance is None or 
            current_time - self.balance_cache_time > self.balance_cache_duration):
            self.cached_balance = self.api.get_balance()
            self.balance_cache_time = current_time
        return self.cached_balance

    def get_order_size(self, capital, price):
        """Calculate order size based on available balance and leverage"""
        wallet_balance = self.get_cached_balance()
        if price > 0:
            # Calculate position size based on configured percentage of available balance with configured leverage
            order_size = int((POSITION_SIZE_PERCENT * wallet_balance * LEVERAGE / price) * 1000)
        else:
            order_size = 10
        if order_size < 1:
            order_size = 1
        return order_size

    def calculate_stop_loss(self, entry_price, supertrend_price, position, order_size=None):
        """Calculate stop loss based on SuperTrend or percentage-based fallback"""
        if not pd.isna(supertrend_price) and supertrend_price > 0:
            return supertrend_price
        else:
            if order_size is not None:
                total_invested_capital = order_size * entry_price * 0.001
                capital_reduction = total_invested_capital * 0.10
                if position == 'LONG':
                    return entry_price - (capital_reduction / (order_size * 0.001))
                else:
                    return entry_price + (capital_reduction / (order_size * 0.001))
            else:
                if position == 'LONG':
                    return entry_price * 0.90
                else:
                    return entry_price * 1.10

    def decide(self, df, capital):
        """Main strategy decision logic"""
        if df is None or df.empty or len(df) < 2:
            return {'action': None, 'side': None, 'qty': 0, 'price': 0, 'stop_loss': None}
            
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        signal = last['supertrend_signal']
        prev_signal = prev['supertrend_signal']
        mark_price = self.api.get_latest_price()
        
        if mark_price is None:
            raise Exception('Could not fetch mark price from Delta API')
            
        supertrend_price = last['supertrend']
        action = None
        order_size = 0
        
        # First trade logic
        if not self.first_trade_done and self.position is None:
            if signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'LONG', order_size)
                self.first_trade_done = True
            elif signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'SHORT', order_size)
                self.first_trade_done = True
                
        # Position reversal logic (no current position)
        elif self.position is None:
            if prev_signal == -1 and signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'LONG', order_size)
            elif prev_signal == 1 and signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'SHORT', order_size)
                
        # Currently LONG position
        elif self.position == 'LONG':
            if prev_signal == 1 and signal == -1:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'SHORT', order_size)
            elif self.stop_loss is not None and last['low'] <= self.stop_loss:
                action = 'SELL'
                self.position = 'SHORT'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'SHORT', order_size)
                
        # Currently SHORT position
        elif self.position == 'SHORT':
            if prev_signal == -1 and signal == 1:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'LONG', order_size)
            elif self.stop_loss is not None and last['high'] >= self.stop_loss:
                action = 'BUY'
                self.position = 'LONG'
                self.entry_price = mark_price
                order_size = self.get_order_size(capital, mark_price)
                self.stop_loss = self.calculate_stop_loss(mark_price, supertrend_price, 'LONG', order_size)
        
        return {
            'action': action,
            'side': self.position,
            'qty': order_size,
            'price': mark_price,
            'stop_loss': self.stop_loss
        }
