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
        self.exchange_position_state = None
        self.last_position_check = None
        
    def check_exchange_position_state(self):
        """Check and update the current position state from the exchange"""
        try:
            # Get account state from exchange
            account_state = self.api.get_account_state(product_id=84)
            self.exchange_position_state = account_state
            
            # Update position tracking
            if account_state.get('has_positions', False):
                # Get actual position details
                positions = self.api.get_positions(product_id=84)
                if positions and len(positions) > 0:
                    # Use the first position (assuming single product trading)
                    pos = positions[0]
                    self.position = {
                        'side': 'buy' if pos.get('side', '').lower() == 'long' else 'sell',
                        'size': abs(float(pos.get('size', 0))),
                        'unrealized_pnl': float(pos.get('unrealized_pnl', 0)),
                        'entry_price': float(pos.get('entry_price', 0)),
                        'mark_price': float(pos.get('mark_price', 0))
                    }
                    self.logger.info(f"Position detected: {self.position}")
                else:
                    self.position = None
                    self.logger.info("No active positions found")
            else:
                self.position = None
                self.logger.info("No positions detected in account state")
                
            self.last_position_check = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error checking exchange position state: {e}")
            # Keep existing position state if check fails
            
    def ensure_ready_for_new_trades(self):
        """Ensure the strategy is ready to place new trades"""
        try:
            # Check if we have recent position state
            if self.last_position_check is None:
                self.check_exchange_position_state()
                
            # Verify no conflicting orders exist
            try:
                orders = self.api.get_live_orders()
                if orders and len(orders) > 0:
                    self.logger.info(f"Found {len(orders)} existing orders - strategy ready for new trades")
                else:
                    self.logger.info("No existing orders - strategy ready for new trades")
            except Exception as e:
                self.logger.warning(f"Could not check existing orders: {e}")
                
            self.logger.info("Strategy is ready for new trades")
            
        except Exception as e:
            self.logger.error(f"Error ensuring strategy readiness: {e}")
        
    def decide(self, candles: pd.DataFrame, capital: float, iteration_number: int = None) -> Optional[Dict]:
        """
        Make trading decision based on SuperTrend signals and current market conditions
        
        Args:
            candles: DataFrame with OHLCV data and SuperTrend indicators
            capital: Available capital for trading
            iteration_number: Current iteration number for logging
            
        Returns:
            Dict with trading decision or None if no action
        """
        try:
            if candles is None or candles.empty:
                self.logger.warning("No candle data available for decision making")
                return None
                
            # Log available columns for debugging
            iteration_prefix = f"[Iteration {iteration_number}] " if iteration_number else ""
            self.logger.info(f"{iteration_prefix}Available columns: {list(candles.columns)}")
            
            # Get current SuperTrend signal and value
            current_signal = self._get_supertrend_signal(candles)
            current_supertrend_value = self._get_supertrend_value(candles)
            
            if current_signal is None:
                self.logger.warning(f"{iteration_prefix}No SuperTrend signal available - skipping decision")
                return None
                
            # Get current position from exchange state
            current_position = self._get_current_position()
            
            # Get current price
            current_price = self._get_current_price(candles)
            if current_price is None:
                self.logger.warning(f"{iteration_prefix}No current price available - skipping decision")
                return None
                
            # Calculate position size
            position_size = self._calculate_position_size(capital, current_price)
            
            # Log iteration details
            self.logger.info(f"{iteration_prefix}SuperTrend Direction: {'BUY' if current_signal == 1 else 'SELL' if current_signal == -1 else 'NEUTRAL'}")
            self.logger.info(f"{iteration_prefix}SuperTrend Value: {current_supertrend_value:.2f}")
            self.logger.info(f"{iteration_prefix}Current Price: {current_price:.2f}")
            self.logger.info(f"{iteration_prefix}Position Size: {position_size:.4f}")
            self.logger.info(f"{iteration_prefix}Available Capital: {capital:.2f}")
            
            if current_position:
                self.logger.info(f"{iteration_prefix}Current Position: Side={current_position.get('side', 'Unknown')}, Size={current_position.get('size', 0):.4f}, Cashflow={current_position.get('unrealized_pnl', 0):.2f}")
            else:
                self.logger.info(f"{iteration_prefix}No current position detected")
            
            # Make trading decision
            decision = self._make_trading_decision(
                current_signal, 
                current_position, 
                current_price, 
                position_size
            )
            
            if decision:
                self.logger.info(f"{iteration_prefix}Trading Decision: {decision}")
                self.last_signal = current_signal
            else:
                self.logger.info(f"{iteration_prefix}No trading decision generated")
                
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in strategy decision: {e}")
            return None
    
    def _get_supertrend_signal(self, candles: pd.DataFrame) -> Optional[int]:
        """Extract SuperTrend signal from candles data"""
        try:
            # First try to get the signal from supertrend_signal column (as used in main.py)
            if 'supertrend_signal' in candles.columns:
                latest_signal = candles['supertrend_signal'].iloc[-1]
                if not pd.isna(latest_signal):
                    self.logger.info(f"Using supertrend_signal column: {latest_signal}")
                    return int(latest_signal)
            
            # Fallback: calculate signal from supertrend column vs close price
            if 'supertrend' in candles.columns:
                latest_supertrend = candles['supertrend'].iloc[-1]
                close_price = candles['close'].iloc[-1]
                
                if pd.isna(latest_supertrend) or pd.isna(close_price):
                    return None
                    
                # Determine signal based on SuperTrend vs close price
                if close_price > latest_supertrend:
                    signal = 1  # BUY signal
                elif close_price < latest_supertrend:
                    signal = -1  # SELL signal
                else:
                    signal = 0  # Neutral
                    
                self.logger.info(f"Calculated signal from supertrend vs close: {signal} (Close: {close_price:.2f}, SuperTrend: {latest_supertrend:.2f})")
                return signal
            else:
                self.logger.warning("Neither supertrend_signal nor supertrend column found in candles data")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting SuperTrend signal: {e}")
            return None
    
    def _get_supertrend_value(self, candles: pd.DataFrame) -> Optional[float]:
        """Extract SuperTrend value from candles data"""
        try:
            if 'supertrend' not in candles.columns:
                return None
                
            # Get the latest SuperTrend value
            latest_supertrend = candles['supertrend'].iloc[-1]
            
            if pd.isna(latest_supertrend):
                return None
                
            return float(latest_supertrend)
                
        except Exception as e:
            self.logger.error(f"Error getting SuperTrend value: {e}")
            return None
    
    def _get_current_position(self) -> Optional[Dict]:
        """Get current position from exchange state"""
        try:
            # Use the position we tracked from exchange state
            if self.position is not None:
                return self.position
            else:
                # Fallback: check exchange directly if we don't have cached state
                try:
                    account_state = self.api.get_account_state(product_id=84)
                    if account_state.get('has_positions', False):
                        positions = self.api.get_positions(product_id=84)
                        if positions and len(positions) > 0:
                            pos = positions[0]
                            self.position = {
                                'side': 'buy' if pos.get('side', '').lower() == 'long' else 'sell',
                                'size': abs(float(pos.get('size', 0))),
                                'unrealized_pnl': float(pos.get('unrealized_pnl', 0)),
                                'entry_price': float(pos.get('entry_price', 0)),
                                'mark_price': float(pos.get('mark_price', 0))
                            }
                            return self.position
                except Exception as e:
                    self.logger.warning(f"Could not get position from exchange: {e}")
                
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
            if capital <= 0:
                self.logger.warning(f"Invalid capital: {capital}")
                return 0.0
                
            if price <= 0:
                self.logger.warning(f"Invalid price: {price}")
                return 0.0
                
            # Use 50% of available capital
            position_value = capital * 0.5
            position_size = position_value / price
            
            # Round to appropriate decimal places
            rounded_size = round(position_size, 6)
            
            self.logger.info(f"Position size calculation: Capital={capital:.2f}, Price={price:.2f}, Position Value={position_value:.2f}, Size={rounded_size:.6f}")
            
            # Validate minimum position size
            if rounded_size < 0.000001:  # Minimum BTC size
                self.logger.warning(f"Position size too small: {rounded_size:.6f}")
                return 0.0
                
            return rounded_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _make_trading_decision(self, signal: int, position: Optional[Dict], 
                              price: float, size: float) -> Optional[Dict]:
        """Make trading decision based on signals and current state"""
        try:
            self.logger.info(f"Making trading decision - Signal: {signal}, Position: {position}, Price: {price:.2f}, Size: {size:.6f}")
            
            # If no signal, no action
            if signal == 0:
                self.logger.info("No SuperTrend signal - no action needed")
                return None
                
            # If we have a position, check if we need to close it
            if position:
                self.logger.info(f"Position exists - checking if closure needed. Signal: {signal}, Position side: {position.get('side', 'Unknown')}")
                decision = self._handle_position_management(signal, position, price, size)
                if decision:
                    self.logger.info(f"Position management decision: {decision}")
                else:
                    self.logger.info("No position management action needed")
                return decision
            
            # If no position, check if we should open one
            if signal != 0:
                self.logger.info(f"No position - creating entry decision for signal: {signal}")
                decision = self._create_entry_decision(signal, price, size)
                if decision:
                    self.logger.info(f"Entry decision created: {decision}")
                else:
                    self.logger.warning("Failed to create entry decision")
                return decision
                
            self.logger.warning(f"Unexpected state - Signal: {signal}, Position: {position}")
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
                self.logger.info(f"Signal reversal detected - closing position. Signal: {signal}, Position: {position_side}")
                return {
                    'action': 'CLOSE',
                    'side': 'LONG' if position_side == 'buy' else 'SHORT',
                    'qty': abs(float(position.get('size', 0))),
                    'price': price,
                    'stop_loss': price,  # Market close
                    'reason': 'Signal reversal'
                }
            else:
                self.logger.info(f"Position maintained - signal aligns with current position. Signal: {signal}, Position: {position_side}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling position management: {e}")
            return None
    
    def _create_entry_decision(self, signal: int, price: float, size: float) -> Optional[Dict]:
        """Create entry decision for new position"""
        try:
            # Validate inputs
            if signal not in [1, -1]:
                self.logger.error(f"Invalid signal for entry decision: {signal}")
                return None
                
            if price <= 0:
                self.logger.error(f"Invalid price for entry decision: {price}")
                return None
                
            if size <= 0:
                self.logger.error(f"Invalid size for entry decision: {size}")
                return None
                
            # Calculate stop loss (2% below/above entry for buy/sell)
            stop_loss_pct = 0.02
            if signal == 1:  # BUY
                stop_loss = price * (1 - stop_loss_pct)
                side = 'LONG'
                self.logger.info(f"Creating BUY decision: Price: {price:.2f}, Stop Loss: {stop_loss:.2f}, Size: {size:.6f}")
            else:  # SELL
                stop_loss = price * (1 + stop_loss_pct)
                side = 'SHORT'
                self.logger.info(f"Creating SELL decision: Price: {price:.2f}, Stop Loss: {stop_loss:.2f}, Size: {size:.6f}")
            
            decision = {
                'action': 'OPEN',
                'side': side,
                'qty': size,
                'price': price,
                'stop_loss': stop_loss,
                'reason': f'SuperTrend {side} signal'
            }
            
            # Validate decision structure
            required_keys = ['action', 'side', 'qty', 'price', 'stop_loss', 'reason']
            if not all(key in decision for key in required_keys):
                self.logger.error(f"Invalid decision structure: {decision}")
                return None
                
            self.logger.info(f"Entry decision validated successfully: {decision}")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error creating entry decision: {e}")
            return None
