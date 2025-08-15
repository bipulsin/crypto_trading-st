#!/bin/bash

# EC2 Server Setup Script for React Frontend
# Run this script on your EC2 instance to prepare it for deployment

set -e

echo "🔧 Setting up EC2 server for React Frontend deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "📦 Installing essential packages..."
sudo apt install -y \
    nginx \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Node.js (for PM2 and potential future use)
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PM2 globally
echo "📦 Installing PM2..."
sudo npm install -g pm2

# Configure firewall (if ufw is enabled)
if command -v ufw &> /dev/null; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    sudo ufw --force enable
    echo "✅ Firewall configured"
fi

# Create nginx directories
echo "📁 Creating nginx directories..."
sudo mkdir -p /var/www/trademanthan-frontend
sudo mkdir -p /var/log/nginx/trademanthan-frontend

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chown -R www-data:www-data /var/www/trademanthan-frontend
sudo chmod -R 755 /var/www/trademanthan-frontend

# Create nginx configuration
echo "⚙️ Creating nginx configuration..."
sudo tee /etc/nginx/sites-available/trademanthan-frontend > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;  # Will match any domain/IP
    
    root /var/www/trademanthan-frontend;
    index index.html;
    
    # Logs
    access_log /var/log/nginx/trademanthan-frontend/access.log;
    error_log /var/log/nginx/trademanthan-frontend/error.log;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Handle React Router
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy to Python backend
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

# Enable the site
echo "🔗 Enabling nginx site..."
sudo ln -sf /etc/nginx/sites-available/trademanthan-frontend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
sudo nginx -t

# Start and enable nginx
echo "🚀 Starting nginx..."
sudo systemctl start nginx
sudo systemctl enable nginx

# Create PM2 ecosystem file for Python backend
echo "📝 Creating PM2 ecosystem file..."
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'trademanthan-api',
    script: 'app.py',
    interpreter: 'python3',
    cwd: '/home/ubuntu/crypto_trading_1',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 5000
    },
    error_file: '/home/ubuntu/crypto_trading_1/logs/pm2-error.log',
    out_file: '/home/ubuntu/crypto_trading_1/logs/pm2-out.log',
    log_file: '/home/ubuntu/crypto_trading_1/logs/pm2-combined.log',
    time: true
  }]
}
EOF

# Create logs directory
mkdir -p /home/ubuntu/crypto_trading_1/logs

# Create deployment script
echo "📝 Creating deployment helper script..."
cat > deploy-react.sh << 'EOF'
#!/bin/bash

# Quick deployment script for React frontend updates
# Usage: ./deploy-react.sh

echo "🚀 Deploying React frontend update..."

# Stop nginx temporarily
sudo systemctl stop nginx

# Create backup
if [ -d "/var/www/trademanthan-frontend" ]; then
    sudo cp -r /var/www/trademanthan-frontend /var/www/trademanthan-frontend-backup-$(date +%Y%m%d-%H%M%S)
fi

# Extract new deployment (assuming file is uploaded to /tmp/react-frontend-*.tar.gz)
cd /tmp
LATEST_PACKAGE=$(ls -t react-frontend-*.tar.gz | head -1)
if [ -n "$LATEST_PACKAGE" ]; then
    sudo tar -xzf "$LATEST_PACKAGE" -C /var/www/trademanthan-frontend
    sudo mv /var/www/trademanthan-frontend/build/* /var/www/trademanthan-frontend/
    sudo rmdir /var/www/trademanthan-frontend/build
    
    # Set permissions
    sudo chown -R www-data:www-data /var/www/trademanthan-frontend
    sudo chmod -R 755 /var/www/trademanthan-frontend
    
    echo "✅ Deployment completed"
else
    echo "❌ No deployment package found in /tmp"
    exit 1
fi

# Start nginx
sudo systemctl start nginx

# Clean up
rm -f /tmp/react-frontend-*.tar.gz

echo "🎉 React frontend deployment completed!"
EOF

chmod +x deploy-react.sh

# Create systemd service for Python backend (alternative to PM2)
echo "📝 Creating systemd service for Python backend..."
sudo tee /etc/systemd/system/trademanthan-api.service > /dev/null << 'EOF'
[Unit]
Description=Trade Manthan API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto_trading_1
Environment=PATH=/home/ubuntu/crypto_trading_1/venv/bin
ExecStart=/home/ubuntu/crypto_trading_1/venv/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Create health check script
echo "📝 Creating health check script..."
cat > health-check.sh << 'EOF'
#!/bin/bash

# Health check script for the application
# Usage: ./health-check.sh

echo "🏥 Performing health check..."

# Check nginx status
echo "📊 Nginx Status:"
sudo systemctl status nginx --no-pager -l | head -10

# Check if React app is accessible
echo ""
echo "🌐 React App Health:"
if curl -s http://localhost/health > /dev/null; then
    echo "✅ React app is responding"
else
    echo "❌ React app is not responding"
fi

# Check if Python backend is accessible
echo ""
echo "🐍 Python Backend Health:"
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Python backend is responding"
else
    echo "❌ Python backend is not responding"
fi

# Check disk usage
echo ""
echo "💾 Disk Usage:"
df -h /var/www/trademanthan-frontend

# Check memory usage
echo ""
echo "🧠 Memory Usage:"
free -h

echo ""
echo "🏥 Health check completed!"
EOF

chmod +x health-check.sh

# Create log rotation configuration
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/trademanthan-frontend > /dev/null << 'EOF'
/var/log/nginx/trademanthan-frontend/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}
EOF

# Final status check
echo ""
echo "🎉 EC2 server setup completed successfully!"
echo ""
echo "📋 Summary of what was installed:"
echo "   ✅ Nginx web server"
echo "   ✅ Node.js and PM2"
echo "   ✅ Firewall configuration"
echo "   ✅ Nginx configuration for React app"
echo "   ✅ PM2 ecosystem file for Python backend"
echo "   ✅ Systemd service for Python backend"
echo "   ✅ Deployment helper script"
echo "   ✅ Health check script"
echo "   ✅ Log rotation configuration"
echo ""
echo "🚀 Next steps:"
echo "   1. Upload your React build files to /tmp/"
echo "   2. Run: ./deploy-react.sh"
echo "   3. Ensure your Python backend is running"
echo "   4. Test your application"
echo ""
echo "🔧 Useful commands:"
echo "   - Check nginx status: sudo systemctl status nginx"
echo "   - Check nginx logs: sudo tail -f /var/log/nginx/trademanthan-frontend/error.log"
echo "   - Health check: ./health-check.sh"
echo "   - Deploy updates: ./deploy-react.sh"
echo ""
echo "🌐 Your React app will be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
