#!/bin/bash

# Google OAuth Configuration Script for Trade Manthan Web Application

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

print_status "Google OAuth Configuration for Trade Manthan Web Application"
echo "=================================================================="
echo ""

print_warning "Before running this script, make sure you have:"
echo "1. Created a Google Cloud Project"
echo "2. Enabled Google+ API and Google OAuth2 API"
echo "3. Created OAuth 2.0 credentials"
echo "4. Set authorized redirect URIs to:"
echo "   - http://13.115.183.85/callback"
echo "   - https://13.115.183.85/callback"
echo ""

read -p "Do you have your Google OAuth credentials ready? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_error "Please set up your Google OAuth credentials first."
    echo ""
    print_status "Steps to get credentials:"
    echo "1. Go to: https://console.developers.google.com/"
    echo "2. Create a new project"
    echo "3. Enable Google+ API and Google OAuth2 API"
    echo "4. Create OAuth 2.0 credentials"
    echo "5. Set redirect URIs to: http://13.115.183.85/callback"
    echo ""
    exit 1
fi

echo ""
print_status "Please enter your Google OAuth credentials:"
echo ""

read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
read -s -p "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
echo ""
read -p "Enter your domain/IP (e.g., 13.115.183.85): " DOMAIN
read -s -p "Enter a strong secret key for Flask (at least 32 characters): " FLASK_SECRET_KEY
echo ""

# Validate inputs
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$DOMAIN" ] || [ -z "$FLASK_SECRET_KEY" ]; then
    print_error "All fields are required!"
    exit 1
fi

print_status "Updating application configuration..."

# Update the systemd service file
ssh -i trademanthan.pem ubuntu@13.115.183.85 << EOF
    # Update service file with new credentials
    sudo sed -i "s/your-google-client-id/$GOOGLE_CLIENT_ID/g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s/your-google-client-secret/$GOOGLE_CLIENT_SECRET/g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/systemd/system/trade-manthan-web.service
    sudo sed -i "s|your-production-secret-key-change-this|$FLASK_SECRET_KEY|g" /etc/systemd/system/trade-manthan-web.service
    
    # Update nginx configuration
    sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/trade-manthan-web
    
    # Reload systemd and restart services
    sudo systemctl daemon-reload
    sudo systemctl restart nginx
    sudo systemctl restart trade-manthan-web
    
    echo "Configuration updated successfully!"
EOF

print_success "Google OAuth configuration completed!"
echo ""
print_status "Your application should now be accessible at:"
echo "  http://$DOMAIN"
echo "  https://$DOMAIN (if SSL is configured)"
echo ""
print_status "Test the Google OAuth login by visiting the application."
echo ""
print_warning "If you still get OAuth errors, please check:"
echo "1. Your redirect URIs are exactly: http://$DOMAIN/callback"
echo "2. Your Google Cloud project has the required APIs enabled"
echo "3. Your OAuth consent screen is configured"
echo ""
print_status "To check application status:"
echo "  ssh -i trademanthan.pem ubuntu@$DOMAIN"
echo "  sudo systemctl status trade-manthan-web"
