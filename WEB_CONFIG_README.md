# 🌐 Web Configuration System

A web-based configuration interface for your trading bot that allows you to modify `config.py` variables through a browser.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-cors
```

### 2. Start the Web Server
```bash
python3 start_web_config.py
```

### 3. Access the Dashboard
Open your browser and go to: **http://localhost:5000**

## 📋 Features

### ✅ **Web Dashboard**
- Modern, responsive interface
- Real-time configuration editing
- Form validation
- Visual feedback

### ✅ **Configuration Management**
- Edit all trading parameters
- Real-time validation
- Automatic backups before changes
- Configuration restore functionality

### ✅ **API Endpoints**
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/backups` - List configuration backups
- `POST /api/backups/<filename>` - Restore from backup
- `POST /api/validate` - Validate configuration changes

### ✅ **Safety Features**
- Automatic backup creation before changes
- Configuration validation
- Error handling and logging
- Rollback capability

## 🛠️ Configuration Variables

### **Trading Configuration**
- `LEVERAGE` - Trading leverage (1-100x)
- `POSITION_SIZE_PERCENT` - Percentage of balance per trade (0.01-1.0)
- `TAKE_PROFIT_MULTIPLIER` - Risk-reward ratio (0.1-10.0)
- `ST_WITH_TRAILING` - Enable/disable trailing stop

### **SuperTrend Parameters**
- `SUPERTREND_PERIOD` - Lookback period (1-50)
- `SUPERTREND_MULTIPLIER` - ATR multiplier (0.1-10.0)

### **Risk Management**
- `MAX_CAPITAL_LOSS_PERCENT` - Maximum loss percentage (1-100%)
- `DEFAULT_CAPITAL` - Default capital if balance unavailable

### **Order Management**
- `RESPECT_EXISTING_ORDERS` - Respect existing orders on startup
- `AUTO_CANCEL_OLD_ORDERS` - Auto-cancel old orders
- `MAX_ORDER_AGE_HOURS` - Maximum order age (1-168 hours)

### **Performance Settings**
- `MAX_ITERATION_TIME` - Maximum iteration time (0.1-10.0 seconds)
- `PENDING_ORDER_MAX_ITERATIONS` - Max iterations for pending orders (1-10)

### **Trading Timing**
- `ENABLE_CONTINUOUS_MONITORING` - Enable continuous monitoring
- `ENABLE_CANDLE_CLOSE_ENTRIES` - Only place orders at candle close
- `MONITORING_INTERVAL` - Monitoring interval (10-3600 seconds)

## 🔧 Usage

### **Starting the Server**
```bash
# Method 1: Use the startup script (recommended)
python3 start_web_config.py

# Method 2: Run directly
python3 web_config.py
```

### **Accessing the Dashboard**
1. Start the server
2. Open your browser
3. Navigate to `http://localhost:5000`
4. The dashboard will load automatically

### **Making Changes**
1. **Load Current Config**: Click "Reload Current" to load existing settings
2. **Edit Values**: Modify the configuration values in the form
3. **Validate**: Click "Validate" to check if changes are valid
4. **Save**: Click "Save Configuration" to apply changes

### **Backup Management**
- **Automatic Backups**: Created before each configuration change
- **Manual Restore**: Use the backup section to restore previous configurations
- **Backup Location**: `config_backups/` directory

## 📁 File Structure

```
crypto_trading_1/
├── web_config.py              # Main Flask application
├── start_web_config.py        # Startup script
├── templates/
│   └── config_dashboard.html  # Web dashboard template
├── config_backups/            # Configuration backups
│   ├── config_backup_20250805_143022.py
│   └── ...
└── config.py                  # Configuration file (modified by web interface)
```

## 🔒 Security Considerations

### **Local Access Only**
- Server runs on `localhost` by default
- No external access unless configured
- Use firewall rules for additional security

### **Backup Protection**
- Automatic backups before changes
- Timestamped backup files
- Easy rollback capability

### **Validation**
- Input validation on all parameters
- Range checking for numeric values
- Type validation for boolean values

## 🚨 Troubleshooting

### **Port Already in Use**
```bash
# Check what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use a different port
python3 web_config.py --port 5001
```

### **Permission Errors**
```bash
# Make files executable
chmod +x start_web_config.py
chmod +x web_config.py
```

### **Dependencies Missing**
```bash
# Install manually
pip install flask flask-cors

# Or use the startup script which auto-installs
python3 start_web_config.py
```

### **Configuration File Issues**
```bash
# Check if config.py exists
ls -la config.py

# Restore from backup if needed
cp config_backups/config_backup_YYYYMMDD_HHMMSS.py config.py
```

## 🔄 Integration with Trading Bot

### **Automatic Reload**
The web configuration system automatically reloads the `config` module after changes, so your trading bot will use the new settings on the next iteration.

### **Running Both Simultaneously**
You can run both the web configuration server and the trading bot at the same time:

```bash
# Terminal 1: Start web config
python3 start_web_config.py

# Terminal 2: Start trading bot
python3 strategy_st.py
```

### **Configuration Changes**
1. Make changes through the web interface
2. The `config.py` file is updated automatically
3. The trading bot will pick up changes on the next iteration
4. No need to restart the trading bot

## 📊 API Documentation

### **Get Configuration**
```bash
curl http://localhost:5000/api/config
```

### **Update Configuration**
```bash
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"LEVERAGE": 50, "POSITION_SIZE_PERCENT": 0.75}'
```

### **Validate Configuration**
```bash
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"LEVERAGE": 50, "POSITION_SIZE_PERCENT": 0.75}'
```

### **List Backups**
```bash
curl http://localhost:5000/api/backups
```

### **Restore Backup**
```bash
curl -X POST http://localhost:5000/api/backups/config_backup_20250805_143022.py
```

## 🎯 Best Practices

### **Before Making Changes**
1. Always validate configuration changes
2. Check current trading bot status
3. Ensure no critical trades are in progress

### **After Making Changes**
1. Monitor the trading bot behavior
2. Check logs for any errors
3. Verify that new settings are applied correctly

### **Backup Strategy**
1. Keep multiple backups
2. Test configuration changes on testnet first
3. Document significant changes

## 🆘 Support

If you encounter issues:

1. **Check Logs**: Look for error messages in the terminal
2. **Restore Backup**: Use the backup functionality to restore previous settings
3. **Restart Server**: Stop and restart the web configuration server
4. **Check Dependencies**: Ensure all required packages are installed

## 🔮 Future Enhancements

- [ ] User authentication
- [ ] Configuration profiles
- [ ] Real-time trading bot status
- [ ] Configuration change history
- [ ] Email notifications for changes
- [ ] Mobile-responsive design improvements 