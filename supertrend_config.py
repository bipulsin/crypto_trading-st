#!/usr/bin/env python3
"""
SuperTrend Strategy Configuration
This file contains all configurable parameters for the SuperTrend trading strategy
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SuperTrendConfig:
    """Configuration class for SuperTrend strategy"""
    
    def __init__(self, user_id: Optional[str] = None, strategy_name: str = "supertrend"):
        self.user_id = user_id
        self.strategy_name = strategy_name
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables and database"""
        # API Configuration
        self.base_url = os.getenv('BASE_URL', 'https://api.delta.exchange')
        self.api_key = os.getenv('API_KEY', '')
        self.api_secret = os.getenv('API_SECRET', '')
        
        # Trading Configuration
        self.symbol = os.getenv('STRATEGY_SYMBOL', 'BTCUSD')
        self.symbol_id = os.getenv('STRATEGY_SYMBOL_ID', '84')  # Default to BTCUSD testnet
        self.leverage = int(os.getenv('LEVERAGE', '1'))
        self.candle_size = os.getenv('STRATEGY_CANDLE_SIZE', '5m')
        
        # SuperTrend Parameters
        self.st_period = int(os.getenv('STRATEGY_ST_PERIOD', '10'))
        self.st_multiplier = float(os.getenv('STRATEGY_ST_MULTIPLIER', '3.0'))
        
        # Risk Management
        self.position_size_pct = float(os.getenv('STRATEGY_POSITION_SIZE_PCT', '0.5'))
        self.take_profit_multiplier = float(os.getenv('STRATEGY_TAKE_PROFIT_MULTIPLIER', '1.5'))
        self.max_capital_loss = float(os.getenv('STRATEGY_MAX_CAPITAL_LOSS', '0.1'))
        self.default_capital = float(os.getenv('STRATEGY_DEFAULT_CAPITAL', '1000.0'))
        
        # Trailing Stop Configuration
        self.trailing_stop_enabled = os.getenv('STRATEGY_TRAILING_STOP', 'false').lower() == 'true'
        self.trailing_stop_distance = float(os.getenv('STRATEGY_TRAILING_STOP_DISTANCE', '100'))
        
        # Order Management
        self.order_timeout_iterations = int(os.getenv('STRATEGY_ORDER_TIMEOUT_ITERATIONS', '3'))
        self.position_close_wait_time = int(os.getenv('STRATEGY_POSITION_CLOSE_WAIT_TIME', '2'))
        
        # Logging Configuration
        self.log_level = os.getenv('STRATEGY_LOG_LEVEL', 'INFO')
        self.log_to_file = os.getenv('STRATEGY_LOG_TO_FILE', 'true').lower() == 'true'
        self.log_to_database = os.getenv('STRATEGY_LOG_TO_DATABASE', 'true').lower() == 'true'
        
        # Performance Monitoring
        self.performance_tracking = os.getenv('STRATEGY_PERFORMANCE_TRACKING', 'true').lower() == 'true'
        self.max_drawdown_threshold = float(os.getenv('STRATEGY_MAX_DRAWDOWN_THRESHOLD', '0.15'))
        
        # Advanced Features
        self.adaptive_parameters = os.getenv('STRATEGY_ADAPTIVE_PARAMETERS', 'false').lower() == 'true'
        self.market_regime_detection = os.getenv('STRATEGY_MARKET_REGIME_DETECTION', 'false').lower() == 'true'
        self.volatility_adjustment = os.getenv('STRATEGY_VOLATILITY_ADJUSTMENT', 'false').lower() == 'true'
    
    def get_symbol_mapping(self) -> Dict[str, Dict[str, str]]:
        """Get symbol ID mapping for different environments"""
        return {
            'BTCUSD': {
                'testnet': '84',
                'live': '27'
            },
            'ETHUSD': {
                'testnet': '3137',  # Placeholder - verify with Delta Exchange
                'live': '3136'
            },
            'SOLUSD': {
                'testnet': '3138',  # Placeholder - verify with Delta Exchange
                'live': '3139'
            }
        }
    
    def get_environment_type(self) -> str:
        """Determine if current environment is testnet or live"""
        if 'testnet' in self.base_url.lower() or 'sandbox' in self.base_url.lower():
            return 'testnet'
        return 'live'
    
    def get_symbol_id_for_symbol(self, symbol: str) -> str:
        """Get the correct symbol ID based on symbol and environment"""
        mapping = self.get_symbol_mapping()
        environment = self.get_environment_type()
        
        if symbol in mapping and environment in mapping[symbol]:
            return mapping[symbol][environment]
        
        # Fallback to default
        return self.symbol_id
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        if not self.api_key:
            validation_results['errors'].append("API_KEY is required")
            validation_results['valid'] = False
        
        if not self.api_secret:
            validation_results['errors'].append("API_SECRET is required")
            validation_results['valid'] = False
        
        # Validate SuperTrend parameters
        if self.st_period < 1 or self.st_period > 100:
            validation_results['errors'].append("ST_PERIOD must be between 1 and 100")
            validation_results['valid'] = False
        
        if self.st_multiplier < 0.1 or self.st_multiplier > 10.0:
            validation_results['errors'].append("ST_MULTIPLIER must be between 0.1 and 10.0")
            validation_results['valid'] = False
        
        # Validate risk parameters
        if self.position_size_pct <= 0 or self.position_size_pct > 1:
            validation_results['errors'].append("POSITION_SIZE_PCT must be between 0 and 1")
            validation_results['valid'] = False
        
        if self.take_profit_multiplier <= 0:
            validation_results['errors'].append("TAKE_PROFIT_MULTIPLIER must be positive")
            validation_results['valid'] = False
        
        if self.max_capital_loss <= 0 or self.max_capital_loss > 1:
            validation_results['errors'].append("MAX_CAPITAL_LOSS must be between 0 and 1")
            validation_results['valid'] = False
        
        # Warnings for potentially risky settings
        if self.leverage > 10:
            validation_results['warnings'].append("High leverage detected - consider reducing for safety")
        
        if self.position_size_pct > 0.8:
            validation_results['warnings'].append("High position size detected - consider reducing for risk management")
        
        return validation_results
    
    def get_config_summary(self) -> str:
        """Get a formatted summary of the current configuration"""
        summary = f"""
=== SuperTrend Strategy Configuration ===
User ID: {self.user_id or 'Not set'}
Strategy: {self.strategy_name}

API Configuration:
  Base URL: {self.base_url}
  Environment: {self.get_environment_type()}
  API Key: {'Set' if self.api_key else 'Not set'}
  API Secret: {'Set' if self.api_secret else 'Not set'}

Trading Configuration:
  Symbol: {self.symbol}
  Symbol ID: {self.symbol_id}
  Leverage: {self.leverage}x
  Candle Size: {self.candle_size}

SuperTrend Parameters:
  Period: {self.st_period}
  Multiplier: {self.st_multiplier}

Risk Management:
  Position Size: {self.position_size_pct * 100}%
  Take Profit Multiplier: {self.take_profit_multiplier}
  Max Capital Loss: {self.max_capital_loss * 100}%
  Default Capital: ${self.default_capital}

Trailing Stop:
  Enabled: {self.trailing_stop_enabled}
  Distance: {self.trailing_stop_distance}

Advanced Features:
  Adaptive Parameters: {self.adaptive_parameters}
  Market Regime Detection: {self.market_regime_detection}
  Volatility Adjustment: {self.volatility_adjustment}
"""
        return summary
    
    def export_to_env_format(self) -> str:
        """Export configuration to .env file format"""
        env_content = f"""# SuperTrend Strategy Configuration
# Generated for user: {self.user_id or 'unknown'}

# API Configuration
BASE_URL={self.base_url}
API_KEY={self.api_key}
API_SECRET={self.api_secret}

# Trading Configuration
STRATEGY_SYMBOL={self.symbol}
STRATEGY_SYMBOL_ID={self.symbol_id}
LEVERAGE={self.leverage}
STRATEGY_CANDLE_SIZE={self.candle_size}

# SuperTrend Parameters
STRATEGY_ST_PERIOD={self.st_period}
STRATEGY_ST_MULTIPLIER={self.st_multiplier}

# Risk Management
STRATEGY_POSITION_SIZE_PCT={self.position_size_pct}
STRATEGY_TAKE_PROFIT_MULTIPLIER={self.take_profit_multiplier}
STRATEGY_MAX_CAPITAL_LOSS={self.max_capital_loss}
STRATEGY_DEFAULT_CAPITAL={self.default_capital}

# Trailing Stop Configuration
STRATEGY_TRAILING_STOP={str(self.trailing_stop_enabled).lower()}
STRATEGY_TRAILING_STOP_DISTANCE={self.trailing_stop_distance}

# Order Management
STRATEGY_ORDER_TIMEOUT_ITERATIONS={self.order_timeout_iterations}
STRATEGY_POSITION_CLOSE_WAIT_TIME={self.position_close_wait_time}

# Logging Configuration
STRATEGY_LOG_LEVEL={self.log_level}
STRATEGY_LOG_TO_FILE={str(self.log_to_file).lower()}
STRATEGY_LOG_TO_DATABASE={str(self.log_to_database).lower()}

# Performance Monitoring
STRATEGY_PERFORMANCE_TRACKING={str(self.performance_tracking).lower()}
STRATEGY_MAX_DRAWDOWN_THRESHOLD={self.max_drawdown_threshold}

# Advanced Features
STRATEGY_ADAPTIVE_PARAMETERS={str(self.adaptive_parameters).lower()}
STRATEGY_MARKET_REGIME_DETECTION={str(self.market_regime_detection).lower()}
STRATEGY_VOLATILITY_ADJUSTMENT={str(self.volatility_adjustment).lower()}
"""
        return env_content

def create_default_config(user_id: str, strategy_name: str = "supertrend") -> SuperTrendConfig:
    """Create a default configuration for new users"""
    config = SuperTrendConfig(user_id, strategy_name)
    
    # Set conservative default values
    config.st_period = 10
    config.st_multiplier = 3.0
    config.leverage = 1
    config.position_size_pct = 0.3  # Conservative 30%
    config.take_profit_multiplier = 1.5
    config.max_capital_loss = 0.05  # 5% max loss
    config.trailing_stop_enabled = True
    config.trailing_stop_distance = 100
    
    return config

if __name__ == "__main__":
    # Test configuration
    config = SuperTrendConfig("test_user")
    
    print("Configuration loaded successfully!")
    print(config.get_config_summary())
    
    # Validate configuration
    validation = config.validate_config()
    if validation['valid']:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("⚠️ Configuration warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    # Export to .env format
    print("\n=== Export to .env format ===")
    print(config.export_to_env_format())
