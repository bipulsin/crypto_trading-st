import pandas as pd
import numpy as np
from logger import get_logger
import datetime

# Set up logger
logger = get_logger('live_strategy', 'logs/live_strategy.log')

def log(msg):
    logger.info(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

class LiveStrategy:
    def __init__(self, api):
        self.api = api
        self.position = None  # 'long', 'short', or None
        self.last_signal = None
        
    def decide(self, candles, capital):
        """Make trading decision based on SuperTrend signals"""
        if candles is None or candles.empty:
            return None
            
        # Get latest SuperTrend signal
        latest_signal = int(candles.iloc[-1]['supertrend_signal'])
        latest_price = candles.iloc[-1]['close']
        
        # Calculate position size based on capital and risk
        position_size = self._calculate_position_size(capital, latest_price)
        
        # Trading logic
        if latest_signal == 1 and self.position != 'long':
            # Buy signal
            self.position = 'long'
            return {
                'action': 'buy',
                'side': 'buy',
                'qty': position_size,
                'price': latest_price,
                'stop_loss': candles.iloc[-1]['supertrend']
            }
        elif latest_signal == -1 and self.position != 'short':
            # Sell signal
            self.position = 'short'
            return {
                'action': 'sell',
                'side': 'sell',
                'qty': position_size,
                'price': latest_price,
                'stop_loss': candles.iloc[-1]['supertrend']
            }
        
        self.last_signal = latest_signal
        return None
        
    def _calculate_position_size(self, capital, price):
        """Calculate position size based on capital and risk management"""
        # Simple position sizing: use 95% of capital
        risk_capital = capital * 0.95
        position_size = risk_capital / price
        return round(position_size, 2)

    def reset_position_state(self):
        """Reset position state after position closure"""
        self.position = None
        self.last_signal = None

    def ensure_ready_for_new_trades(self):
        """Ensure strategy is ready for new trades"""
        if self.position is not None:
            self.position = None
        if self.last_signal is not None:
            self.last_signal = None
