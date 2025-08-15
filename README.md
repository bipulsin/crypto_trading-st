# 🚀 Trade Manthan Web - Complete Trading Platform

A comprehensive cryptocurrency trading platform with SuperTrend strategy implementation, web interface, and automated trading capabilities.

## 📋 Project Overview

This workspace contains the complete Trade Manthan Web application extracted from the EC2 production server. It includes:

- **Web Application**: Flask-based trading dashboard with OAuth authentication
- **Trading Strategy**: SuperTrend algorithm implementation
- **API Integration**: Delta Exchange API wrapper
- **Strategy Management**: Database-driven strategy configuration
- **Production Configuration**: Nginx, systemd service, and SSL setup

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and configure your API credentials.

### 3. Run the Application

#### Web Application
```bash
python app.py
```
Access at: http://localhost:5000

#### Trading Strategy (Standalone)
```bash
python main.py
```

## 🔧 Key Features

- **SuperTrend Algorithm**: Period 10, Multiplier 3.0
- **Risk Management**: Position sizing, stop-loss, take-profit
- **Web Interface**: User authentication, strategy dashboard
- **API Integration**: Delta Exchange full trading support
- **Simulation Mode**: Test strategy without real trading

## 🛠️ Development

The workspace includes all production files with the latest fixes:
- Simulation mode support for testing without valid API credentials
- Enhanced error handling and fallback mechanisms
- Updated Delta API with proper environment variable loading
- Complete web application with OAuth authentication

---

**Trade Manthan Web** - Professional Cryptocurrency Trading Platform
