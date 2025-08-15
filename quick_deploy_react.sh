#!/bin/bash

# Quick React Frontend Deployment Script
# Update the variables below and run this script

# ===== CONFIGURATION - UPDATE THESE VALUES =====
EC2_IP="13.115.183.85"        # Your EC2 public IP address
EC2_DOMAIN="trademanthan.in"   # Your domain name (if you have one)
EC2_USER="ubuntu"              # EC2 username (usually 'ubuntu')
EMAIL="admin@trademanthan.in"  # Your email for SSL certificate
# ==============================================

echo "🚀 Quick React Frontend Deployment to EC2"
echo "EC2 IP: $EC2_IP"
echo "Domain: $EC2_DOMAIN"
echo "User: $EC2_USER"
echo "Email: $EMAIL"
echo ""

# Check if configuration is updated
if [ "$EC2_IP" = "your-ec2-ip-address" ] || [ "$EC2_DOMAIN" = "your-domain.com" ]; then
    echo "❌ Please update the configuration variables in this script first!"
    echo "   - EC2_IP: Your EC2 public IP address"
    echo "   - EC2_DOMAIN: Your domain name"
    echo "   - EMAIL: Your email address"
    exit 1
fi

# Build the React app
echo "📦 Building React application..."
npm run build

if [ ! -d "build" ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build completed successfully"

# Create deployment package
echo "📦 Creating deployment package..."
DEPLOY_PACKAGE="react-frontend-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$DEPLOY_PACKAGE" build/

# Upload to EC2
echo "📤 Uploading to EC2..."
scp -o StrictHostKeyChecking=no "$DEPLOY_PACKAGE" "$EC2_USER@$EC2_IP:/tmp/"

# Deploy on EC2
echo "🚀 Deploying on EC2..."
ssh -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << EOF
    # Install nginx if not present
    if ! command -v nginx &> /dev/null; then
        sudo apt update
        sudo apt install -y nginx
    fi
    
    # Create deployment directory
    sudo mkdir -p /var/www/trademanthan-frontend
    
    # Extract new deployment
    cd /tmp
    sudo tar -xzf "$DEPLOY_PACKAGE" -C /var/www/trademanthan-frontend
    sudo mv /var/www/trademanthan-frontend/build/* /var/www/trademanthan-frontend/
    sudo rmdir /var/www/trademanthan-frontend/build
    
    # Set permissions
    sudo chown -R www-data:www-data /var/www/trademanthan-frontend
    sudo chmod -R 755 /var/www/trademanthan-frontend
    
    # Create nginx configuration
    sudo tee /etc/nginx/sites-available/trademanthan-frontend > /dev/null << 'NGINX_CONFIG'
server {
    listen 80;
    server_name $EC2_IP $EC2_DOMAIN;
    
    root /var/www/trademanthan-frontend;
    index index.html;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Handle React Router
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy to Python backend
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX_CONFIG
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/trademanthan-frontend /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload nginx
    sudo nginx -t
    sudo systemctl reload nginx
    sudo systemctl enable nginx
    
    # Clean up
    rm -f /tmp/$DEPLOY_PACKAGE
    
    echo "✅ Deployment completed on EC2"
EOF

# Clean up local package
rm -f "$DEPLOY_PACKAGE"

echo ""
echo "🎉 Deployment completed successfully!"
echo "🌐 Your React app should now be available at:"
echo "   http://$EC2_IP"
if [ "$EC2_DOMAIN" != "your-domain.com" ]; then
    echo "   http://$EC2_DOMAIN"
fi
echo ""
echo "📝 Next steps:"
echo "   1. Test your application at the URLs above"
echo "   2. Set up SSL certificate (optional):"
echo "      ssh $EC2_USER@$EC2_IP 'sudo apt install certbot python3-certbot-nginx'"
echo "      ssh $EC2_USER@$EC2_IP 'sudo certbot --nginx -d $EC2_DOMAIN --non-interactive --agree-tos --email $EMAIL'"
echo "   3. Ensure your Python backend is running on port 5000"
echo ""
echo "🔧 Troubleshooting:"
echo "   - Check nginx status: ssh $EC2_USER@$EC2_IP 'sudo systemctl status nginx'"
echo "   - Check nginx logs: ssh $EC2_USER@$EC2_IP 'sudo tail -f /var/log/nginx/error.log'"
echo "   - Check app directory: ssh $EC2_USER@$EC2_IP 'ls -la /var/www/trademanthan-frontend'"
