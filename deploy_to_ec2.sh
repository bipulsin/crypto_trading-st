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
KEY_FILE="your-key.pem"  # Change this to your key file
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
sudo apt install -y python3 python3-pip python3-venv git nginx

echo "📁 Creating project directory..."
mkdir -p ~/trading-bot
cd ~/trading-bot

echo "📥 Cloning repository..."
if [ -d "crypto_trading-st" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd crypto_trading-st
    git pull origin main
else
    git clone https://github.com/bipulsin/crypto_trading-st.git
    cd crypto_trading-st
fi

echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

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
sudo tee /etc/systemd/system/trading-bot-web-config.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Trading Bot Web Configuration Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trading-bot/crypto_trading-st
Environment=PATH=/home/ubuntu/trading-bot/crypto_trading-st/venv/bin
Environment=WEB_CONFIG_USERNAME=admin
Environment=WEB_CONFIG_PASSWORD=tradingbot2024
Environment=FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
Environment=WEB_CONFIG_PORT=5000
ExecStart=/home/ubuntu/trading-bot/crypto_trading-st/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 web_config:app
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
echo "================================================================"

EOF

print_status "Deployment completed successfully!"
print_status "You can now access your web configuration at: http://43.206.219.70"
print_warning "Remember to change the default password in the web interface!" 