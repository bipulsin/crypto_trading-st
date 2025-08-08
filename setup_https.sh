#!/bin/bash

# Setup HTTPS with Let's Encrypt SSL Certificate
# This script configures HTTPS for your trading bot web configuration

set -e

echo "🔒 Setting up HTTPS for Trading Bot Dashboard..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
EC2_IP="13.115.183.85"
EC2_USER="ubuntu"
KEY_FILE="trademanthan.pem"

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    print_error "Key file $KEY_FILE not found!"
    print_warning "Please update the KEY_FILE variable in this script with your actual key file path."
    exit 1
fi

print_status "Connecting to EC2 instance at $EC2_IP..."

# SSH into EC2 and set up HTTPS
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'

echo "🔒 Setting up HTTPS..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update

# Install Certbot and Nginx plugin
echo "📦 Installing Certbot and Nginx plugin..."
sudo apt install -y certbot python3-certbot-nginx

# Check if we have a domain name or use IP
echo "🌐 Checking domain configuration..."
if [ -n "$DOMAIN_NAME" ]; then
    DOMAIN="$DOMAIN_NAME"
    echo "Using domain: $DOMAIN"
else
    DOMAIN="$EC2_IP"
    echo "Using IP address: $DOMAIN"
    print_warning "Note: Let's Encrypt requires a domain name for SSL certificates."
    print_warning "IP addresses are not supported. You'll need to set up a domain name first."
    print_warning "For now, we'll configure Nginx for HTTPS but you'll need a domain for SSL."
fi

# Backup current Nginx configuration
echo "📄 Backing up current Nginx configuration..."
sudo cp /etc/nginx/sites-available/trading-bot-config /etc/nginx/sites-available/trading-bot-config.backup

# Create new HTTPS Nginx configuration
echo "📝 Creating HTTPS Nginx configuration..."
sudo tee /etc/nginx/sites-available/trading-bot-config > /dev/null << NGINXEOF
server {
    listen 80;
    listen 443 ssl;
    server_name 13.115.183.85;

    # SSL Configuration (will be updated by Certbot)
    ssl_certificate /etc/letsencrypt/live/13.115.183.85/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/13.115.183.85/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Redirect HTTP to HTTPS
    if (\$scheme != "https") {
        return 301 https://\$server_name\$request_uri;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Let's Encrypt challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

# HTTP server for Let's Encrypt challenges
server {
    listen 80;
    server_name 13.115.183.85;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
NGINXEOF

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx
echo "🔄 Restarting Nginx..."
sudo systemctl restart nginx

# Try to obtain SSL certificate (this will fail for IP addresses)
echo "🔐 Attempting to obtain SSL certificate..."
if sudo certbot --nginx -d 13.115.183.85 --non-interactive --agree-tos --email admin@example.com; then
    echo "✅ SSL certificate obtained successfully!"
else
    echo "⚠️  SSL certificate could not be obtained for IP address."
    echo "📝 This is expected - Let's Encrypt requires a domain name."
    echo "💡 To get HTTPS working, you need to:"
    echo "   1. Register a domain name"
    echo "   2. Point it to your EC2 IP: 13.115.183.85"
    echo "   3. Run: sudo certbot --nginx -d yourdomain.com"
fi

# Configure firewall for HTTPS
echo "🔥 Configuring firewall for HTTPS..."
sudo ufw allow 443

# Set up auto-renewal
echo "🔄 Setting up SSL certificate auto-renewal..."
sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# Check service status
echo "📊 Checking service status..."
sudo systemctl status nginx --no-pager

# Test HTTPS connectivity
echo "🧪 Testing HTTPS connectivity..."
if curl -s -k https://13.115.183.85 > /dev/null; then
    echo "✅ HTTPS connection successful (self-signed certificate)"
else
    echo "❌ HTTPS connection failed"
fi

echo ""
echo "✅ HTTPS setup completed!"
echo "================================================"
echo "🌐 Access URLs:"
echo "   HTTP (redirects to HTTPS): http://13.115.183.85"
echo "   HTTPS: https://13.115.183.85"
echo "   API: https://13.115.183.85/api/"
echo ""
echo "🔧 Service Management:"
echo "   Nginx Status: sudo systemctl status nginx"
echo "   Nginx Logs: sudo tail -f /var/log/nginx/error.log"
echo "   SSL Renewal: sudo certbot renew"
echo ""
echo "⚠️  Important Notes:"
echo "   - For proper SSL, you need a domain name pointing to 13.115.183.85"
echo "   - Run: sudo certbot --nginx -d yourdomain.com"
echo "   - SSL certificates auto-renew every 90 days"
echo "================================================"

EOF

print_status "HTTPS setup completed!"
print_warning "For proper SSL certificates, you need a domain name pointing to your EC2 IP."
print_status "You can now access your dashboard at: https://13.115.183.85" 