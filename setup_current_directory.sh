#!/bin/bash

# Setup script for current root directory with Python 3.10.2
# Usage: ./setup_current_directory.sh

set -e

echo "🔧 Setting up Trading Bot Web Configuration in current directory..."
echo "================================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check Python version
print_status "Checking Python installation..."
python3 --version

# Check if we're in the right directory
if [ ! -f "web_config.py" ]; then
    print_warning "web_config.py not found in current directory"
    print_status "Current directory: $(pwd)"
    print_status "Files in current directory:"
    ls -la
    echo ""
    read -p "Continue anyway? (y/n): " continue_choice
    if [ "$continue_choice" != "y" ]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Setup virtual environment
print_status "Setting up virtual environment..."
if [ -d "venv" ]; then
    print_status "Virtual environment exists, activating..."
    source venv/bin/activate
else
    print_status "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

print_status "Python version: $(python3 --version)"
print_status "Virtual environment: $VIRTUAL_ENV"

# Install dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment variables
print_status "Setting up environment variables..."
cat > .env << EOF
WEB_CONFIG_USERNAME=admin
WEB_CONFIG_PASSWORD=tradingbot2024
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
WEB_CONFIG_PORT=5000
EOF

# Create systemd service file
print_status "Creating systemd service file..."
ACTUAL_PROJECT_DIR="$(pwd)"
ACTUAL_VENV_PATH="$ACTUAL_PROJECT_DIR/venv"

sudo tee /etc/systemd/system/trading-bot-web-config.service > /dev/null << EOF
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
EOF

# Set up Nginx
print_status "Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/trading-bot-config > /dev/null << EOF
server {
    listen 80;
    server_name 43.206.219.70;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/trading-bot-config /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Configure firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Start the service
print_status "Starting web configuration service..."
sudo systemctl daemon-reload
sudo systemctl enable trading-bot-web-config
sudo systemctl start trading-bot-web-config

# Show status
print_status "Checking service status..."
sudo systemctl status trading-bot-web-config --no-pager

echo ""
echo "✅ Setup completed successfully!"
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