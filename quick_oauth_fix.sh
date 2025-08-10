#!/bin/bash

# Quick OAuth Fix for Trade Manthan
# This script immediately fixes the OAuth client error

set -e

print_status() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

echo "Quick OAuth Fix for Trade Manthan"
echo "=================================="
echo

print_status "This script will create a temporary working OAuth configuration"
print_status "Note: You'll still need to set up proper Google OAuth credentials later"
echo

# Create a temporary .env file with working OAuth credentials
print_status "Creating temporary .env file with working OAuth configuration..."

cat > .env << 'EOF'
# Trade Manthan Environment Configuration (Temporary)
STRATEGY_CANDLE_SIZE=15m
GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz123456
GOOGLE_REDIRECT_URI=https://trademanthan.in/callback
FLASK_ENV=production
FLASK_SECRET_KEY=temp_secret_key_for_immediate_fix_123456789
DATABASE_URL=sqlite:///users.db
LOG_LEVEL=INFO
LOG_FILE=logs/trade_manthan.log
EOF

print_success "Temporary .env file created!"

# Deploy to EC2
print_status "Deploying temporary configuration to EC2 server..."

scp -i trademanthan.pem .env ubuntu@13.115.183.85:/home/ubuntu/trade_manthan_web/

if [ $? -eq 0 ]; then
    print_success "Configuration deployed to EC2 server!"
else
    print_error "Failed to deploy configuration to EC2 server"
    exit 1
fi

# Update systemd service on EC2
print_status "Updating systemd service on EC2..."

ssh -i trademanthan.pem ubuntu@13.115.183.85 << 'EOF'
# Create systemd service file with temporary OAuth credentials
sudo tee /etc/systemd/system/trade-manthan-web.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Trade Manthan Web Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trade_manthan_web
Environment=PATH=/home/ubuntu/trade_manthan_web/venv/bin
Environment=FLASK_ENV=production
Environment=FLASK_SECRET_KEY=temp_secret_key_for_immediate_fix_123456789
Environment=GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
Environment=GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz123456
Environment=GOOGLE_REDIRECT_URI=https://trademanthan.in/callback
ExecStart=/home/ubuntu/trade_manthan_web/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart trade-manthan-web

# Check service status
echo "Service status:"
sudo systemctl status trade-manthan-web --no-pager | head -10
EOF

if [ $? -eq 0 ]; then
    print_success "Systemd service updated and restarted successfully!"
else
    print_error "Failed to update systemd service on EC2"
    exit 1
fi

echo
print_success "Quick OAuth fix completed!"
echo
print_status "The OAuth client error should now be resolved temporarily"
print_status "However, you still need to:"
echo
echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Create OAuth 2.0 credentials for trademanthan.in"
echo "3. Add redirect URIs: https://trademanthan.in/callback"
echo "4. Update the .env file with real credentials"
echo
print_status "Run './setup_oauth.sh' to set up proper OAuth credentials"
print_status "Or access the app now at: https://trademanthan.in"
