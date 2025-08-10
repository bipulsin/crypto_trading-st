#!/usr/bin/env python3

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

class LiveStrategy:
    """
    Live SuperTrend Strategy implementation for making trading decisions
    """
    
    def __init__(self, api):
        self.api = api
        self.logger = logging.getLogger(__name__)
        self.last_signal = None
        self.position = None
        
    def decide(self, candles: pd.DataFrame, capital: float) -> Optional[Dict]:
        """
        Make trading decision based on SuperTrend signals and current market conditions
        
        Args:
            candles: DataFrame with OHLCV data and SuperTrend indicators
            capital: Available capital for trading
            
        Returns:
            Dict with trading decision or None if no action
        """
        try:
            if candles is None or candles.empty:
                self.logger.warning("No candle data available for decision making")
                return None
                
            # Get current SuperTrend signal
            current_signal = self._get_supertrend_signal(candles)
            if current_signal is None:
                return None
                
            # Get current position
            current_position = self._get_current_position()
            
            # Get current price
            current_price = self._get_current_price(candles)
            if current_price is None:
                return None
                
            # Calculate position size
            position_size = self._calculate_position_size(capital, current_price)
            
            # Make trading decision
            decision = self._make_trading_decision(
                current_signal, 
                current_position, 
                current_price, 
                position_size
            )
            
            if decision:
                self.logger.info(f"Trading decision: {decision}")
                self.last_signal = current_signal
                
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in strategy decision: {e}")
            return None
    
    def _get_supertrend_signal(self, candles: pd.DataFrame) -> Optional[int]:
        """Extract SuperTrend signal from candles data"""
        try:
            if 'supertrend' not in candles.columns:
                self.logger.warning("SuperTrend column not found in candles data")
                return None
                
            # Get the latest SuperTrend value
            latest_supertrend = candles['supertrend'].iloc[-1]
            close_price = candles['close'].iloc[-1]
            
            if pd.isna(latest_supertrend):
                return None
                
            # Determine signal based on SuperTrend vs close price
            if close_price > latest_supertrend:
                return 1  # BUY signal
            elif close_price < latest_supertrend:
                return -1  # SELL signal
            else:
                return 0  # Neutral
                
        except Exception as e:
            self.logger.error(f"Error getting SuperTrend signal: {e}")
            return None
    
    def _get_current_position(self) -> Optional[Dict]:
        """Get current position from exchange"""
        try:
            # This would typically call the API to get current position
            # For now, return None (no position)
            return None
        except Exception as e:
            self.logger.error(f"Error getting current position: {e}")
            return None
    
    def _get_current_price(self, candles: pd.DataFrame) -> Optional[float]:
        """Get current market price"""
        try:
            if candles.empty:
                return None
            return float(candles['close'].iloc[-1])
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return None
    
    def _calculate_position_size(self, capital: float, price: float) -> float:
        """Calculate position size based on capital and risk management"""
        try:
            # Use 50% of available capital
            position_value = capital * 0.5
            position_size = position_value / price
            
            # Round to appropriate decimal places
            return round(position_size, 6)
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _make_trading_decision(self, signal: int, position: Optional[Dict], 
                              price: float, size: float) -> Optional[Dict]:
        """Make trading decision based on signals and current state"""
        try:
            # If no signal, no action
            if signal == 0:
                return None
                
            # If we have a position, check if we need to close it
            if position:
                return self._handle_position_management(signal, position, price, size)
            
            # If no position, check if we should open one
            if signal != 0:
                return self._create_entry_decision(signal, price, size)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error making trading decision: {e}")
            return None
    
    def _handle_position_management(self, signal: int, position: Dict, 
                                  price: float, size: float) -> Optional[Dict]:
        """Handle existing position management"""
        try:
            position_side = position.get('side', '').lower()
            
            # If signal is opposite to position, close position
            if (signal == 1 and position_side == 'sell') or \
               (signal == -1 and position_side == 'buy'):
                return {
                    'action': 'CLOSE',
                    'side': 'LONG' if position_side == 'buy' else 'SHORT',
                    'qty': abs(float(position.get('size', 0))),
                    'price': price,
                    'stop_loss': price,  # Market close
                    'reason': 'Signal reversal'
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling position management: {e}")
            return None
    
    def _create_entry_decision(self, signal: int, price: float, size: float) -> Optional[Dict]:
        """Create entry decision for new position"""
        try:
            # Calculate stop loss (2% below/above entry for buy/sell)
            stop_loss_pct = 0.02
            if signal == 1:  # BUY
                stop_loss = price * (1 - stop_loss_pct)
                side = 'LONG'
            else:  # SELL
                stop_loss = price * (1 + stop_loss_pct)
                side = 'SHORT'
            
            return {
                'action': 'OPEN',
                'side': side,
                'qty': size,
                'price': price,
                'stop_loss': stop_loss,
                'reason': f'SuperTrend {side} signal'
            }
            
        except Exception as e:
            self.logger.error(f"Error creating entry decision: {e}")
            return None
