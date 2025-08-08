#!/bin/bash

# Update Domain Configuration Script for Trade Manthan Web Application

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

print_status "Updating Trade Manthan Web Application for domain: trademanthan.in"
echo "======================================================================"
echo ""

# Configuration
DOMAIN="trademanthan.in"
WWW_DOMAIN="www.trademanthan.in"
EC2_HOST="13.115.183.85"

print_status "Updating nginx configuration..."

# Update nginx configuration
ssh -i trademanthan.pem ubuntu@$EC2_HOST << EOF
    # Update nginx configuration
    sudo sed -i "s/server_name.*;/server_name $DOMAIN $WWW_DOMAIN;/g" /etc/nginx/sites-available/trade-manthan-web
    
    # Test nginx configuration
    sudo nginx -t
    
    # Reload nginx
    sudo systemctl reload nginx
    
    echo "Nginx configuration updated successfully!"
EOF

print_success "Nginx configuration updated!"

print_status "Updating systemd service configuration..."

# Get OAuth credentials from user or environment variables
echo ""
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    print_warning "Please provide your Google OAuth credentials:"
    read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
else
    print_status "Using Google Client ID from environment variable"
fi

if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    read -s -p "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
    echo ""
else
    print_status "Using Google Client Secret from environment variable"
fi

if [ -z "$FLASK_SECRET_KEY" ]; then
    read -s -p "Enter a strong secret key for Flask (at least 32 characters): " FLASK_SECRET_KEY
    echo ""
else
    print_status "Using Flask Secret Key from environment variable"
fi

# Validate inputs
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$FLASK_SECRET_KEY" ]; then
    print_error "All fields are required!"
    exit 1
fi

# Update systemd service
ssh -i trademanthan.pem ubuntu@$EC2_HOST << EOF
    # Update service file with new credentials and domain
    sudo sed -i "s/your-google-client-id/$GOOGLE_CLIENT_ID/g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s/your-google-client-secret/$GOOGLE_CLIENT_SECRET/g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s|your-production-secret-key-change-this|$FLASK_SECRET_KEY|g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s|https://your-domain.com/callback|https://$DOMAIN/callback|g" /etc/systemd/system/trade-manthan-web.service
    
    # Reload systemd and restart service
    sudo systemctl daemon-reload
    sudo systemctl restart trade-manthan-web
    
    echo "Systemd service updated successfully!"
EOF

print_success "Systemd service updated!"

print_status "Testing application..."

# Test the application
sleep 5
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN || echo "000")
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN 2>/dev/null || echo "000")

echo ""
print_status "Domain Configuration Results:"
echo "=================================="
echo "Domain: $DOMAIN"
echo "WWW Domain: $WWW_DOMAIN"
echo "EC2 IP: $EC2_HOST"
echo ""
echo "HTTP Status: $HTTP_STATUS"
echo "HTTPS Status: $HTTPS_STATUS"
echo ""

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
    print_success "HTTP access is working!"
else
    print_warning "HTTP access may not be working yet. DNS propagation can take time."
fi

if [ "$HTTPS_STATUS" = "200" ] || [ "$HTTPS_STATUS" = "302" ]; then
    print_success "HTTPS access is working!"
else
    print_warning "HTTPS access may not be working yet. SSL certificate may need to be configured."
fi

echo ""
print_status "Next Steps:"
echo "============="
echo "1. Wait for DNS propagation (15 minutes to 48 hours)"
echo "2. Test your application at: http://$DOMAIN"
echo "3. Configure SSL certificate for HTTPS (recommended)"
echo ""
print_status "To configure SSL certificate:"
echo "  ssh -i trademanthan.pem ubuntu@$EC2_HOST"
echo "  cd /home/ubuntu/trade_manthan_web"
echo "  ./setup_ssl.sh"
echo ""
print_status "To check application status:"
echo "  ssh -i trademanthan.pem ubuntu@$EC2_HOST"
echo "  sudo systemctl status trade-manthan-web"
echo ""
print_success "Domain configuration completed!"
