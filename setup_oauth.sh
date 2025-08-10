#!/bin/bash

# OAuth Setup Script for Trade Manthan
# This script helps you set up Google OAuth credentials

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=" * 60
echo "GOOGLE OAUTH SETUP FOR TRADE MANTHAN"
echo "=" * 60
echo

print_status "This script will help you set up Google OAuth credentials for trademanthan.in"
echo

print_warning "BEFORE RUNNING THIS SCRIPT, you need to:"
echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Create a new project or select existing one"
echo "3. Enable Google+ API and Google OAuth2 API"
echo "4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID"
echo "5. Set Application Type to 'Web application'"
echo "6. Add Authorized redirect URIs:"
echo "   - https://trademanthan.in/callback"
echo "   - http://trademanthan.in/callback"
echo "7. Copy the Client ID and Client Secret"
echo

read -p "Have you completed the Google Cloud Console setup? (y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Please complete the Google Cloud Console setup first, then run this script again."
    exit 1
fi

echo
print_status "Now let's configure the OAuth credentials..."
echo

# Get OAuth credentials
read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
read -s -p "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
echo

if [[ -z "$GOOGLE_CLIENT_ID" ]] || [[ -z "$GOOGLE_CLIENT_SECRET" ]]; then
    print_error "OAuth credentials cannot be empty"
    exit 1
fi

# Generate a secure Flask secret key
FLASK_SECRET_KEY=$(openssl rand -hex 32)

print_status "Creating .env file with OAuth credentials..."

# Create .env file
cat > .env << EOF
# Trade Manthan Environment Configuration
STRATEGY_CANDLE_SIZE=15m
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI=https://trademanthan.in/callback
FLASK_ENV=production
FLASK_SECRET_KEY=$FLASK_SECRET_KEY
DATABASE_URL=sqlite:///users.db
LOG_LEVEL=INFO
LOG_FILE=logs/trade_manthan.log
EOF

print_success ".env file created successfully!"

# Deploy to EC2
print_status "Deploying OAuth configuration to EC2 server..."

# Copy .env file to EC2
scp -i trademanthan.pem .env ubuntu@13.115.183.85:/home/ubuntu/trade_manthan_web/

if [ $? -eq 0 ]; then
    print_success ".env file deployed to EC2 server!"
else
    print_error "Failed to deploy .env file to EC2 server"
    exit 1
fi

# Update systemd service on EC2
print_status "Updating systemd service configuration on EC2..."

ssh -i trademanthan.pem ubuntu@13.115.183.85 << 'EOF'
# Create systemd service file with proper OAuth credentials
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
Environment=FLASK_SECRET_KEY=$(grep FLASK_SECRET_KEY /home/ubuntu/trade_manthan_web/.env | cut -d'=' -f2)
Environment=GOOGLE_CLIENT_ID=$(grep GOOGLE_CLIENT_ID /home/ubuntu/trade_manthan_web/.env | cut -d'=' -f2)
Environment=GOOGLE_CLIENT_SECRET=$(grep GOOGLE_CLIENT_SECRET /home/ubuntu/trade_manthan_web/.env | cut -d'=' -f2)
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
print_success "OAuth setup completed successfully!"
echo
print_status "Your Trade Manthan application should now work with Google OAuth!"
print_status "Access it at: https://trademanthan.in"
echo
print_warning "If you still see OAuth errors, please check:"
echo "1. The redirect URIs in Google Cloud Console match exactly"
echo "2. The domain trademanthan.in is verified in Google Cloud Console"
echo "3. The OAuth consent screen is configured properly"
echo
print_status "You can check the service status with: ssh -i trademanthan.pem ubuntu@13.115.183.85 'sudo systemctl status trade-manthan-web'"
