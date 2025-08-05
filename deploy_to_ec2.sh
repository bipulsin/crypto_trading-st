#!/bin/bash

# EC2 Deployment Script for Trading Bot Web Configuration
# Usage: ./deploy_to_ec2.sh

set -e  # Exit on any error

echo "🚀 Starting EC2 deployment for Trading Bot Web Configuration..."
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
EC2_IP="43.206.219.70"
EC2_USER="ubuntu"
KEY_FILE="trademanthan.pem"  # Change this to your key file
REPO_URL="https://github.com/bipulsin/crypto_trading-st.git"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    print_error "Key file $KEY_FILE not found!"
    print_warning "Please update the KEY_FILE variable in this script with your actual key file path."
    exit 1
fi

print_status "Connecting to EC2 instance at $EC2_IP..."

# SSH into EC2 and run deployment commands
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'

echo "🔧 Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "📦 Installing required packages..."
sudo apt install -y git nginx
echo "✅ Python 3.10.2 already installed - skipping Python installation"

echo "📁 Setting up project directory..."
echo "Current location: $(pwd)"

# Ask user preference for directory structure
echo ""
echo "🔧 Directory Structure Options:"
echo "1. Use current root directory (current setup)"
echo "2. Move to ~/trading-bot directory (recommended)"
echo "3. Create new ~/trading-bot directory and copy files"

read -p "Choose option (1/2/3): " dir_choice

case $dir_choice in
    1)
        echo "📁 Using current root directory..."
        PROJECT_DIR="$(pwd)"
        ;;
    2)
        echo "📁 Moving to ~/trading-bot directory..."
        mkdir -p ~/trading-bot
        if [ -d "crypto_trading-st" ]; then
            echo "Moving existing crypto_trading-st to ~/trading-bot/"
            mv crypto_trading-st ~/trading-bot/
        fi
        PROJECT_DIR="$HOME/trading-bot"
        ;;
    3)
        echo "📁 Creating new ~/trading-bot directory..."
        mkdir -p ~/trading-bot
        PROJECT_DIR="$HOME/trading-bot"
        ;;
    *)
        echo "Invalid choice. Using current directory..."
        PROJECT_DIR="$(pwd)"
        ;;
esac

cd "$PROJECT_DIR"

echo "📥 Setting up repository..."
if [ -d "crypto_trading-st" ]; then
    echo "Repository exists, pulling latest changes..."
    cd crypto_trading-st
    git pull origin main
else
    echo "Cloning repository..."
    git clone https://github.com/bipulsin/crypto_trading-st.git
    cd crypto_trading-st
fi

echo "🐍 Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment exists, activating..."
    source venv/bin/activate
else
    echo "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

echo "✅ Python version: $(python3 --version)"
echo "✅ Virtual environment: $VIRTUAL_ENV"

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔐 Setting up environment variables..."
cat > .env << 'ENVEOF'
WEB_CONFIG_USERNAME=admin
WEB_CONFIG_PASSWORD=tradingbot2024
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
WEB_CONFIG_PORT=5000
ENVEOF

echo "📄 Creating systemd service file..."
# Get the actual project directory for the service file
ACTUAL_PROJECT_DIR="$(pwd)"
ACTUAL_VENV_PATH="$ACTUAL_PROJECT_DIR/venv"

sudo tee /etc/systemd/system/trading-bot-web-config.service > /dev/null << SERVICEEOF
[Unit]
Description=Trading Bot Web Configuration Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$ACTUAL_PROJECT_DIR
Environment=PATH=$ACTUAL_VENV_PATH/bin
Environment=WEB_CONFIG_USERNAME=admin
Environment=WEB_CONFIG_PASSWORD=tradingbot2024
Environment=FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
Environment=WEB_CONFIG_PORT=5000
ExecStart=$ACTUAL_VENV_PATH/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 web_config:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo "🔧 Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/trading-bot-config > /dev/null << 'NGINXEOF'
server {
    listen 80;
    server_name 43.206.219.70;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

echo "🔗 Enabling Nginx site..."
sudo ln -sf /etc/nginx/sites-available/trading-bot-config /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "🔥 Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

echo "🚀 Starting web configuration service..."
sudo systemctl daemon-reload
sudo systemctl enable trading-bot-web-config
sudo systemctl start trading-bot-web-config

echo "✅ Deployment completed!"
echo "================================================================"
echo "📁 Project Location: $ACTUAL_PROJECT_DIR"
echo "🐍 Python Version: $(python3 --version)"
echo "🔧 Virtual Environment: $ACTUAL_VENV_PATH"
echo ""
echo "🌐 Access URLs:"
echo "   Dashboard: http://43.206.219.70"
echo "   API: http://43.206.219.70/api/"
echo ""
echo "👤 Login Credentials:"
echo "   Username: admin"
echo "   Password: tradingbot2024"
echo ""
echo "🔧 Service Management:"
echo "   Status: sudo systemctl status trading-bot-web-config"
echo "   Logs: sudo journalctl -u trading-bot-web-config -f"
echo "   Restart: sudo systemctl restart trading-bot-web-config"
echo "   Stop: sudo systemctl stop trading-bot-web-config"
echo ""
echo "📁 File Locations:"
echo "   Config: $ACTUAL_PROJECT_DIR/config.py"
echo "   Logs: sudo journalctl -u trading-bot-web-config"
echo "   Service: /etc/systemd/system/trading-bot-web-config.service"
echo "================================================================"

EOF

print_status "Deployment completed successfully!"
print_status "You can now access your web configuration at: http://43.206.219.70"
print_warning "Remember to change the default password in the web interface!" 