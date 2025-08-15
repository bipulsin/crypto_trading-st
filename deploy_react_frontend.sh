#!/bin/bash

# React Frontend Deployment Script for EC2
# This script builds and deploys the React application to your EC2 server

set -e  # Exit on any error

echo "🚀 Starting React Frontend Deployment to EC2..."

# Configuration
REPO_NAME="crypto_trading_1"
BRANCH="main"
EC2_USER="ubuntu"
EC2_HOST="your-ec2-ip-or-domain.com"  # Update this with your EC2 IP/domain
EC2_PATH="/home/ubuntu/trademanthan-frontend"
NGINX_CONFIG_PATH="/etc/nginx/sites-available/trademanthan-frontend"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/trademanthan-frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "src/App.tsx" ]; then
    print_error "This script must be run from the React project root directory"
    exit 1
fi

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 16+ first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "git is not installed. Please install git first."
        exit 1
    fi
    
    print_success "All dependencies are available"
}

# Install dependencies
install_dependencies() {
    print_status "Installing npm dependencies..."
    npm ci --production=false
    print_success "Dependencies installed successfully"
}

# Build the React application
build_app() {
    print_status "Building React application for production..."
    
    # Create production environment file
    cat > .env.production << EOF
REACT_APP_API_URL=https://your-ec2-domain.com
REACT_APP_APP_NAME=Trade Manthan
REACT_APP_VERSION=1.0.0
EOF
    
    # Build the app
    npm run build
    
    if [ ! -d "build" ]; then
        print_error "Build failed - build directory not found"
        exit 1
    fi
    
    print_success "React application built successfully"
}

# Deploy to EC2
deploy_to_ec2() {
    print_status "Deploying to EC2 server..."
    
    # Create deployment package
    DEPLOY_PACKAGE="react-frontend-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "$DEPLOY_PACKAGE" build/
    
    print_status "Uploading to EC2..."
    scp -o StrictHostKeyChecking=no "$DEPLOY_PACKAGE" "$EC2_USER@$EC2_HOST:/tmp/"
    
    print_status "Extracting and deploying on EC2..."
    ssh -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'ENDSSH'
        # Stop nginx temporarily
        sudo systemctl stop nginx
        
        # Create backup of current deployment
        if [ -d "$EC2_PATH" ]; then
            sudo cp -r "$EC2_PATH" "${EC2_PATH}-backup-$(date +%Y%m%d-%H%M%S)"
        fi
        
        # Create deployment directory
        sudo mkdir -p "$EC2_PATH"
        
        # Extract new deployment
        cd /tmp
        sudo tar -xzf "$DEPLOY_PACKAGE" -C "$EC2_PATH"
        sudo mv "$EC2_PATH/build"/* "$EC2_PATH/"
        sudo rmdir "$EC2_PATH/build"
        
        # Set proper permissions
        sudo chown -R www-data:www-data "$EC2_PATH"
        sudo chmod -R 755 "$EC2_PATH"
        
        # Clean up
        rm -f "$DEPLOY_PACKAGE"
        
        # Start nginx
        sudo systemctl start nginx
        
        # Check nginx status
        sudo systemctl status nginx --no-pager -l
ENDSSH
    
    # Clean up local package
    rm -f "$DEPLOY_PACKAGE"
    
    print_success "Deployment completed successfully"
}

# Setup Nginx configuration
setup_nginx() {
    print_status "Setting up Nginx configuration..."
    
    # Create nginx configuration
    cat > nginx-trademanthan-frontend.conf << EOF
server {
    listen 80;
    server_name your-ec2-domain.com www.your-ec2-domain.com;  # Update this
    
    root $EC2_PATH;
    index index.html;
    
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
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Handle React Router
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API proxy to your Python backend
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    
    print_status "Uploading Nginx configuration to EC2..."
    scp -o StrictHostKeyChecking=no nginx-trademanthan-frontend.conf "$EC2_USER@$EC2_HOST:/tmp/"
    
    print_status "Installing Nginx configuration on EC2..."
    ssh -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'ENDSSH'
        # Install nginx if not present
        if ! command -v nginx &> /dev/null; then
            sudo apt update
            sudo apt install -y nginx
        fi
        
        # Copy nginx configuration
        sudo cp /tmp/nginx-trademanthan-frontend.conf "$NGINX_CONFIG_PATH"
        
        # Enable site
        sudo ln -sf "$NGINX_CONFIG_PATH" "$NGINX_ENABLED_PATH"
        
        # Remove default site
        sudo rm -f /etc/nginx/sites-enabled/default
        
        # Test nginx configuration
        sudo nginx -t
        
        # Reload nginx
        sudo systemctl reload nginx
        
        # Enable nginx to start on boot
        sudo systemctl enable nginx
        
        # Clean up
        rm -f /tmp/nginx-trademanthan-frontend.conf
ENDSSH
    
    # Clean up local config
    rm -f nginx-trademanthan-frontend.conf
    
    print_success "Nginx configuration setup completed"
}

# Setup SSL with Let's Encrypt
setup_ssl() {
    print_status "Setting up SSL certificate with Let's Encrypt..."
    
    ssh -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'ENDSSH'
        # Install certbot if not present
        if ! command -v certbot &> /dev/null; then
            sudo apt update
            sudo apt install -y certbot python3-certbot-nginx
        fi
        
        # Get SSL certificate
        sudo certbot --nginx -d your-ec2-domain.com -d www.your-ec2-domain.com --non-interactive --agree-tos --email your-email@example.com
        
        # Test auto-renewal
        sudo certbot renew --dry-run
        
        # Add cron job for auto-renewal
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
ENDSSH
    
    print_success "SSL certificate setup completed"
}

# Setup PM2 for process management (if needed for API)
setup_pm2() {
    print_status "Setting up PM2 for process management..."
    
    ssh -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'ENDSSH'
        # Install Node.js if not present
        if ! command -v node &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt-get install -y nodejs
        fi
        
        # Install PM2 globally
        sudo npm install -g pm2
        
        # Create PM2 ecosystem file for your Python backend
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
    }
  }]
}
EOF
        
        # Start the application with PM2
        pm2 start ecosystem.config.js
        
        # Save PM2 configuration
        pm2 save
        
        # Setup PM2 to start on boot
        pm2 startup
ENDSSH
    
    print_success "PM2 setup completed"
}

# Main deployment flow
main() {
    print_status "Starting React Frontend Deployment..."
    
    # Update configuration
    print_warning "Please update the following in this script before running:"
    echo "  - EC2_HOST: Your EC2 IP address or domain"
    echo "  - Domain names in nginx configuration"
    echo "  - Email address for SSL certificate"
    
    read -p "Have you updated the configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Please update the configuration first"
        exit 1
    fi
    
    check_dependencies
    install_dependencies
    build_app
    deploy_to_ec2
    setup_nginx
    setup_ssl
    setup_pm2
    
    print_success "🎉 React Frontend Deployment Completed Successfully!"
    print_status "Your application should now be available at: https://your-ec2-domain.com"
    print_status "API backend should be running on port 5000"
}

# Run main function
main "$@"
