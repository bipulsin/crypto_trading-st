#!/bin/bash

# Fix HTTPS Nginx Configuration with Self-Signed Certificate
# This script creates a self-signed certificate and fixes the Nginx configuration

set -e

echo "🔧 Fixing HTTPS Nginx Configuration..."
echo "======================================"

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

# SSH into EC2 and fix the HTTPS configuration
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'

echo "🔧 Fixing HTTPS configuration..."

# Stop Nginx first
echo "🛑 Stopping Nginx..."
sudo systemctl stop nginx

# Create SSL directory if it doesn't exist
echo "📁 Creating SSL directory..."
sudo mkdir -p /etc/ssl/private
sudo mkdir -p /etc/ssl/certs

# Generate self-signed certificate
echo "🔐 Generating self-signed certificate..."
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=TradingBot/CN=13.115.183.85"

# Create new Nginx configuration with self-signed certificate
echo "📝 Creating new Nginx configuration..."
sudo tee /etc/nginx/sites-available/trading-bot-config > /dev/null << NGINXEOF
server {
    listen 80;
    server_name 13.115.183.85;
    
    # Redirect all HTTP traffic to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 13.115.183.85;

    # Self-signed certificate
    ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

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
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Let's Encrypt challenge location (for future use)
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}
NGINXEOF

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

# Start Nginx
echo "🚀 Starting Nginx..."
sudo systemctl start nginx

# Check Nginx status
echo "📊 Checking Nginx status..."
sudo systemctl status nginx --no-pager

# Configure firewall for HTTPS
echo "🔥 Configuring firewall for HTTPS..."
sudo ufw allow 443

# Test HTTPS connectivity
echo "🧪 Testing HTTPS connectivity..."
sleep 3

if curl -s -k https://13.115.183.85 > /dev/null; then
    echo "✅ HTTPS connection successful!"
else
    echo "❌ HTTPS connection failed"
    echo "Checking Nginx logs..."
    sudo tail -n 10 /var/log/nginx/error.log
fi

# Test HTTP to HTTPS redirect
echo "🧪 Testing HTTP to HTTPS redirect..."
if curl -s -I http://13.115.183.85 | grep -q "301"; then
    echo "✅ HTTP to HTTPS redirect working!"
else
    echo "❌ HTTP to HTTPS redirect failed"
fi

echo ""
echo "✅ HTTPS configuration fixed!"
echo "================================================"
echo "🌐 Access URLs:"
echo "   HTTP (redirects to HTTPS): http://13.115.183.85"
echo "   HTTPS: https://13.115.183.85"
echo "   API: https://13.115.183.85/api/"
echo ""
echo "⚠️  Important Notes:"
echo "   - Using self-signed certificate (browser will show security warning)"
echo "   - Click 'Advanced' and 'Proceed to 13.115.183.85 (unsafe)' to access"
echo "   - For proper SSL, register a domain and run:"
echo "     sudo certbot --nginx -d yourdomain.com"
echo ""
echo "🔧 Service Management:"
echo "   Nginx Status: sudo systemctl status nginx"
echo "   Nginx Logs: sudo tail -f /var/log/nginx/error.log"
echo "   SSL Certificate: sudo openssl x509 -in /etc/ssl/certs/nginx-selfsigned.crt -text"
echo "================================================"

EOF

print_status "HTTPS configuration fixed!"
print_warning "Browser will show security warning for self-signed certificate."
print_status "You can now access your dashboard at: https://13.115.183.85" 