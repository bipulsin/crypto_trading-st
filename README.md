# Crypto Trading 1: Live SuperTrend Strategy for Delta Exchange India

This project implements a live trading bot for BTCUSD.P perpetual contracts on Delta Exchange India, using a SuperTrend-based strategy. The bot runs continuously, fetches live prices, calculates SuperTrend on 5-minute candles, and executes trades (long/short) using 100% of available capital.

## Features
- Live price and candle fetching from Delta Exchange India API
- SuperTrend calculation on 5-minute candles
- Automatic trade execution (long/short) as per strategy
- Uses 100% of available capital for each trade
- Logging and error handling

## Setup
1. Clone the repo and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Add your Delta Exchange API credentials to `config.py` or a `.env` file.
3. Run the bot:
   ```bash
   python main.py
   ```

## Files
- `main.py`: Master loop for live trading
- `live_strategy.py`: SuperTrend strategy logic
- `delta_api.py`: API wrapper for Delta Exchange
- `supertrend.py`: SuperTrend indicator calculation
- `config.py`: API keys and parameters

**This bot is for educational purposes. Use at your own risk!**

---

## 1. Create a Shell Script to Run Your Python Script with `caffeinate`

Create a file named `run_trading_bot.sh` in your project directory:

```sh
#!/bin/bash
cd /Users/bipulsahay/crypto_trading_1
/usr/bin/caffeinate -i /usr/bin/python3 main.py
```

Make it executable:
```sh
chmod +x /Users/bipulsahay/crypto_trading_1/run_trading_bot.sh
```

---

## 2. Create a Launch Agent Property List (plist) File

Create a file named `com.bipulsahay.tradingbot.plist` in `~/Library/LaunchAgents/`:

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

---

## 3. Load the Launch Agent

In your terminal, run:
```sh
launchctl load ~/Library/LaunchAgents/com.bipulsahay.tradingbot.plist
```

To start it immediately (if not already running):
```sh
launchctl start com.bipulsahay.tradingbot
```

To stop it:
```sh
launchctl stop com.bipulsahay.tradingbot
```

To unload (remove) it:
```sh
launchctl unload ~/Library/LaunchAgents/com.bipulsahay.tradingbot.plist
```

---

## 4. Check Logs

Your script’s output will be in:
- `/Users/bipulsahay/crypto_trading_1/bot.log`
- `/Users/bipulsahay/crypto_trading_1/bot_error.log`

---

### That’s it!  
Your trading bot will now run as a service, stay alive, and restart if it crashes or you log out and back in.

**Let me know if you want me to generate the shell script and plist file for you!**
