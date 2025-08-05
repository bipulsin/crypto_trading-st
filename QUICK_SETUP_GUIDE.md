# 🚀 Quick Setup Guide for EC2 with Python 3.10.2

This guide is specifically tailored for your EC2 setup with Python 3.10.2 already installed and files in the root directory.

## 📋 Your Current Setup

- **EC2 IP**: 43.206.219.70
- **Python Version**: 3.10.2 (already installed)
- **Current Location**: Root directory
- **Virtual Environment**: Available and working

## 🔧 Quick Setup Options

### **Option 1: Use Current Directory (Simplest)**

```bash
# Make the setup script executable
chmod +x setup_current_directory.sh

# Run the setup
./setup_current_directory.sh
```

This will:
- ✅ Use your existing Python 3.10.2
- ✅ Set up virtual environment in current directory
- ✅ Install all dependencies
- ✅ Create systemd service with correct paths
- ✅ Configure Nginx reverse proxy
- ✅ Start the web configuration server

### **Option 2: Move to Recommended Directory Structure**

```bash
# Run the full deployment script
chmod +x deploy_to_ec2.sh
./deploy_to_ec2.sh

# Choose option 2 when prompted for directory structure
```

### **Option 3: Manual Setup**

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export WEB_CONFIG_USERNAME=admin
export WEB_CONFIG_PASSWORD=tradingbot2024
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export WEB_CONFIG_PORT=5000

# 4. Start production server
python3 start_production_server.py
```

## 🌐 Access Information

After setup, access your web configuration at:

- **Dashboard**: http://43.206.219.70
- **API**: http://43.206.219.70/api/
- **Login**: admin / tradingbot2024

## 🔧 Service Management

```bash
# Check service status
sudo systemctl status trading-bot-web-config

# View logs
sudo journalctl -u trading-bot-web-config -f

# Restart service
sudo systemctl restart trading-bot-web-config

# Stop service
sudo systemctl stop trading-bot-web-config
```

## 📁 File Locations

- **Project Directory**: Current directory (where you run the setup)
- **Config File**: `config.py`
- **Service File**: `/etc/systemd/system/trading-bot-web-config.service`
- **Nginx Config**: `/etc/nginx/sites-available/trading-bot-config`
- **Logs**: `sudo journalctl -u trading-bot-web-config`

## 🔒 Security Features

- ✅ Basic authentication (admin/tradingbot2024)
- ✅ Rate limiting (200/day, 50/hour)
- ✅ CORS restrictions
- ✅ Firewall configuration
- ✅ Nginx reverse proxy
- ✅ Systemd service management

## 🚨 Important Notes

1. **Change Default Password**: Update credentials after first login
2. **Virtual Environment**: Always activate before running: `source venv/bin/activate`
3. **Python Version**: Your 3.10.2 is perfect for this setup
4. **Directory Structure**: Current setup works fine, but consider moving to `~/trading-bot` for better organization

## 🔄 Updates

To update the application:

```bash
# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart trading-bot-web-config
```

## 🆘 Troubleshooting

### **Service Won't Start**
```bash
# Check logs
sudo journalctl -u trading-bot-web-config -f

# Check if virtual environment is correct
sudo systemctl status trading-bot-web-config
```

### **Port Already in Use**
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>
```

### **Permission Issues**
```bash
# Fix file permissions
chmod +x *.py
chmod 644 config.py
```

## 🎯 Recommended Next Steps

1. **Run Option 1** for quickest setup
2. **Test the web interface** at http://43.206.219.70
3. **Change default password** in the web interface
4. **Configure your trading parameters** via the web dashboard
5. **Set up monitoring** if needed

Your setup is ready to go! 🚀 