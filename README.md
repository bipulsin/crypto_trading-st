# 🚀 Crypto Trading Bot - SuperTrend Strategy for Delta Exchange

A sophisticated automated trading bot for BTCUSD perpetual contracts on Delta Exchange, implementing a SuperTrend-based strategy with advanced order management, risk controls, and comprehensive error handling.

## 📋 Table of Contents
- [Overview](#overview)
- [Functional Logic](#functional-logic)
- [Configuration](#configuration)
- [Setup & Installation](#setup--installation)
- [Advanced Features](#advanced-features)
- [Risk Management](#risk-management)
- [Troubleshooting](#troubleshooting)
- [Files Structure](#files-structure)

---

## 🎯 Overview

This bot implements a **SuperTrend-based automated trading strategy** with the following key characteristics:

- **Trading Instrument**: BTCUSD perpetual contracts
- **Timeframe**: 5-minute candles
- **Strategy**: SuperTrend indicator (Period: 10, Multiplier: 3.0)
- **Leverage**: 50x
- **Position Sizing**: 50% of available capital per trade
- **Order Type**: Bracket orders with automatic stop-loss and take-profit

---

## 🔄 Functional Logic - Step-by-Step Analysis

### **🔄 INITIALIZATION PHASE**

#### **Step 1: System Setup**
- **Load Configuration**: Import API keys, trading parameters, and risk settings from `config.py`
- **Initialize Components**: 
  - DeltaAPI wrapper for exchange communication
  - LiveStrategy for trading decisions
  - Global state tracking variables (`prev_supertrend_signal`, `pending_order_iterations`, `last_order_id`)
- **Set Default Capital**: Use `DEFAULT_CAPITAL = 200` if balance unavailable

#### **Step 2: Startup Validation**
- **Check Existing Orders**: Scan for any open orders on startup
- **Validate Positions**: Check for existing positions
- **Handle Old Orders**: Cancel orders older than 24 hours if `AUTO_CANCEL_OLD_ORDERS` is enabled
- **Initialize Order Tracking**: Set up order ID tracking for bracket orders

#### **Step 3: Candle Alignment**
- **Wait for Next Candle**: Align bot execution with 5-minute candle boundaries
- **Synchronize Timing**: Ensure consistent execution timing across iterations

### **📊 DATA ACQUISITION PHASE**

#### **Step 4: Market Data Fetching**
- **Primary Source**: Fetch 5-minute candles from Delta Exchange API
- **Fallback Mechanism**: If Delta fails, use Binance API as backup (`CANDLE_FALLBACK_ENABLED`)
- **Data Validation**: Ensure sufficient data (minimum 100 candles)
- **Error Handling**: Skip iteration if data unavailable

#### **Step 5: Technical Analysis**
- **SuperTrend Calculation**: 
  - Period: 10 candles
  - Multiplier: 3.0
  - Generate buy/sell signals (1 = buy, -1 = sell)
- **Signal Processing**: Extract current and previous signals
- **Price Data**: Get current mark price for order placement

### **🔍 VALIDATION PHASE**

#### **Step 6: Order Validation**
- **Check Existing Orders**: Validate against current SuperTrend signals
- **Risk Assessment**: Ensure orders don't violate risk rules (`MAX_CAPITAL_LOSS_PERCENT = 30%`)
- **Invalid Order Handling**: Cancel orders that conflict with strategy
- **Capital Validation**: Verify sufficient capital for trading

#### **Step 7: Position Validation**
- **Position Check**: Verify existing positions align with strategy
- **Risk Management**: Check for excessive losses
- **Position Management**: Handle position updates and stop-loss modifications

### **🎯 TRADING DECISION PHASE**

#### **Step 8: Strategy Analysis**
- **Signal Detection**: Identify SuperTrend signal changes
- **Position State**: Determine if currently in position or not
- **Order State**: Check for pending orders
- **Decision Matrix**: Apply trading logic based on current state

#### **Step 9: Trading Logic Application**

**Scenario A: Has Position**
- **Signal Change**: If SuperTrend direction changes, close position and open new one
- **No Signal Change**: Update stop-loss to latest SuperTrend value
- **Order Management**: Track and update bracket orders

**Scenario B: No Position, No Orders**
- **New Signal**: Place new order based on SuperTrend signal
- **Position Sizing**: Calculate order size based on capital and leverage
- **Risk Management**: Set stop-loss and take-profit levels

**Scenario C: Pending Orders**
- **Order Monitoring**: Track pending order iterations
- **Timeout Handling**: Force cancel orders after `PENDING_ORDER_MAX_ITERATIONS = 4` iterations
- **Retry Logic**: Place new orders after cancellation

### **⚡ ORDER EXECUTION PHASE**

#### **Step 10: Order Placement**
- **Order Type**: Place bracket orders (limit order with stop-loss and take-profit)
- **Position Sizing**: 
  - Use `POSITION_SIZE_PERCENT = 50%` of available balance
  - Apply `LEVERAGE = 50x`
  - Calculate quantity based on current price
- **Price Calculation**: 
  - Entry: Current mark price
  - Stop Loss: SuperTrend value or 10% fallback
  - Take Profit: `TAKE_PROFIT_MULTIPLIER = 1.5x` of risk

#### **Step 11: Order Management**
- **Order Tracking**: Store order ID for future reference
- **Bracket Updates**: Modify stop-loss as SuperTrend changes
- **Order Verification**: Confirm order placement success
- **Error Recovery**: Handle failed order placements

### **🛡️ RISK MANAGEMENT PHASE**

#### **Step 12: Continuous Monitoring**
- **Loss Limits**: Monitor for `MAX_CAPITAL_LOSS_PERCENT = 30%` maximum capital loss
- **Position Updates**: Track position changes and P&L
- **Order States**: Monitor order status and execution
- **Market Conditions**: Adapt to changing market conditions

#### **Step 13: Order Cancellation**
- **Force Cancellation**: Use CancelAllFilterObject API for bulk cancellation
- **Verification**: Confirm orders are actually cancelled (`CANCELLATION_VERIFICATION_ENABLED`)
- **Retry Mechanism**: Multiple cancellation attempts if needed
- **Fallback Methods**: Individual cancellation if bulk fails

### **🔄 ITERATION CONTROL**

#### **Step 14: Loop Management**
- **Timing Control**: Wait for next 5-minute candle
- **Performance Monitoring**: Track iteration execution time (`MAX_ITERATION_TIME = 2.0s`)
- **Error Recovery**: Handle critical errors and continue
- **State Persistence**: Maintain trading state across iterations

---

## ⚙️ Configuration Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Candle Interval** | 5 minutes | Trading timeframe |
| **SuperTrend Period** | 10 | Technical analysis period |
| **SuperTrend Multiplier** | 3.0 | Signal sensitivity |
| **Leverage** | 50x | Position sizing multiplier |
| **Position Size** | 50% | Capital allocation per trade |
| **Max Loss** | 30% | Risk management limit |
| **Order Timeout** | 4 iterations | Pending order handling |
| **Take Profit Multiplier** | 1.5x | Profit target calculation |
| **Verification Attempts** | 2 | Order cancellation verification |
| **Cancellation Wait Time** | 3s | Delay between cancellation attempts |

---

## 🚀 Setup & Installation

### **Prerequisites**
- Python 3.7+
- Delta Exchange account with API access
- Sufficient capital for trading

### **Installation Steps**

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd crypto_trading_1
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Credentials**
   - Edit `config.py` with your Delta Exchange API credentials
   - Or create a `.env` file with:
     ```
     DELTA_API_KEY_TEST=your_api_key
     DELTA_API_SECRET_TEST=your_api_secret
     ```

4. **Run the Bot**
   ```bash
   python main.py
   ```

### **macOS Service Setup**

Create a shell script `run_trading_bot.sh`:
```bash
#!/bin/bash
cd /Users/bipulsahay/crypto_trading_1
/usr/bin/caffeinate -i /usr/bin/python3 main.py
```

Create launch agent `com.bipulsahay.tradingbot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bipulsahay.tradingbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/bipulsahay/crypto_trading_1/run_trading_bot.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/Users/bipulsahay/crypto_trading_1</string>
    <key>StandardOutPath</key>
    <string>/Users/bipulsahay/crypto_trading_1/bot.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/bipulsahay/crypto_trading_1/bot_error.log</string>
</dict>
</plist>
```

Load the service:
```bash
chmod +x run_trading_bot.sh
launchctl load ~/Library/LaunchAgents/com.bipulsahay.tradingbot.plist
```

---

## 🔧 Advanced Features

### **Order Management**
- **Bracket Orders**: Automatic stop-loss and take-profit placement
- **Order Validation**: Strategy alignment checking against SuperTrend signals
- **Bulk Cancellation**: Efficient order cleanup using CancelAllFilterObject API
- **Order Tracking**: Persistent order ID management for bracket updates
- **Force Cancellation**: Multi-level cancellation with verification

### **Risk Controls**
- **Capital Protection**: Maximum loss limits (30% of capital)
- **Dynamic Position Sizing**: Based on available capital and leverage
- **Stop-Loss Updates**: Real-time SuperTrend-based adjustments
- **Order Verification**: Multiple validation methods for cancellation success
- **Fallback Mechanisms**: Alternative data sources and cancellation methods

### **Reliability Features**
- **Data Fallback**: Binance API backup for candle data
- **Error Recovery**: Graceful error handling with retry mechanisms
- **State Persistence**: Maintain trading state across iterations
- **Performance Monitoring**: Iteration time tracking and optimization
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

### **Utility Scripts**
- **Quick Cancel**: `quick_cancel.py` for manual order cancellation
- **Order Management**: Standalone utilities for order operations

---

## 🛡️ Risk Management

### **Capital Protection**
- **Maximum Loss**: 30% of total capital
- **Position Sizing**: 50% of available balance per trade
- **Leverage Control**: 50x leverage with proper risk calculation

### **Order Safety**
- **Bracket Orders**: Automatic stop-loss and take-profit
- **Order Validation**: Strategy compliance checking
- **Cancellation Verification**: Multiple verification attempts
- **Timeout Handling**: Force cancellation after 4 iterations

### **Market Adaptation**
- **SuperTrend Updates**: Real-time stop-loss adjustments
- **Signal Validation**: Confirm strategy alignment
- **Fallback Data**: Alternative data sources for reliability

---

## 🔍 Troubleshooting

### **Common Issues**

1. **Orders Not Cancelling**
   - Check API permissions
   - Verify order states
   - Use `quick_cancel.py` utility

2. **Slow Performance**
   - Monitor iteration times
   - Check network connectivity
   - Review API rate limits

3. **Data Issues**
   - Verify API credentials
   - Check fallback data sources
   - Review candle data quality

### **Log Files**
- **Main Log**: `bot.log` - Trading activity and decisions
- **Error Log**: `bot_error.log` - Error messages and exceptions

### **Manual Utilities**
```bash
# Quick order cancellation
python quick_cancel.py

# Cancel orders for specific product ID
python quick_cancel.py 84
```

---

## 📁 Files Structure

```
crypto_trading_1/
├── main.py                 # Main trading loop and logic
├── live_strategy.py        # SuperTrend strategy implementation
├── delta_api.py           # Delta Exchange API wrapper
├── supertrend.py          # SuperTrend indicator calculation
├── config.py              # Configuration and parameters
├── quick_cancel.py        # Order cancellation utility
├── requirements.txt       # Python dependencies
├── bot.log               # Trading activity log
├── bot_error.log         # Error log
└── README.md             # This documentation
```

### **Core Components**

- **`main.py`**: Orchestrates the entire trading process
- **`live_strategy.py`**: Implements SuperTrend trading logic
- **`delta_api.py`**: Handles all exchange API interactions
- **`supertrend.py`**: Calculates SuperTrend technical indicator
- **`config.py`**: Centralized configuration management

---

## ⚠️ Disclaimer

**This bot is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss. Use at your own risk and never trade with money you cannot afford to lose.**

- Past performance does not guarantee future results
- Always test thoroughly in a paper trading environment first
- Monitor the bot continuously when running live
- Keep API keys secure and use appropriate permissions
- Consider market conditions and volatility

---

## 📞 Support

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Review log files for error details
3. Verify configuration parameters
4. Test with small amounts first

**Happy Trading! 🚀**
