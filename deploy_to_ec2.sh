#!/bin/bash

# Trade Manthan Web Application EC2 Deployment Script
# This script sets up the complete web application on an EC2 instance

set -e  # Exit on any error

# Configuration
EC2_HOST="13.115.183.85"
EC2_USER="ubuntu"
EC2_KEY_PATH="trademanthan.pem"
APP_NAME="trade_manthan_web"
APP_DIR="/home/$EC2_USER/$APP_NAME"
SERVICE_NAME="trade-manthan-web"

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

print_status "Trade Manthan Web Application - EC2 Deployment"
echo "======================================================"
echo ""
print_status "Using predefined EC2 details:"
echo "  Host: $EC2_HOST"
echo "  User: $EC2_USER"
echo "  Key: $EC2_KEY_PATH"
echo ""

# Check if key file exists
if [ ! -f "$EC2_KEY_PATH" ]; then
    print_error "EC2 key file not found: $EC2_KEY_PATH"
    exit 1
fi

print_status "Starting deployment to EC2 instance: $EC2_HOST"

# Create deployment package
print_status "Creating deployment package..."
DEPLOY_DIR="deploy_package"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy application files
cp app.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/
cp -r templates $DEPLOY_DIR/
cp -r static $DEPLOY_DIR/
cp strategy_manager.py $DEPLOY_DIR/
cp strategy_st.py $DEPLOY_DIR/
cp supertrend.py $DEPLOY_DIR/
cp supertrend_config.py $DEPLOY_DIR/
cp delta_api.py $DEPLOY_DIR/
cp config.py $DEPLOY_DIR/
cp logger.py $DEPLOY_DIR/
cp debug_env.py $DEPLOY_DIR/
cp logo.jpg $DEPLOY_DIR/static/ 2>/dev/null || print_warning "logo.jpg not found, will need to be added manually"

# Create systemd service file
cat > $DEPLOY_DIR/trade-manthan-web.service << 'EOF'
[Unit]
Description=Trade Manthan Web Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trade_manthan_web
Environment=PATH=/home/ubuntu/trade_manthan_web/venv/bin
Environment=FLASK_ENV=production
Environment=FLASK_SECRET_KEY=your-production-secret-key-change-this
Environment=GOOGLE_CLIENT_ID=your-google-client-id
Environment=GOOGLE_CLIENT_SECRET=your-google-client-secret
Environment=GOOGLE_REDIRECT_URI=https://your-domain.com/callback
ExecStart=/home/ubuntu/trade_manthan_web/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
cat > $DEPLOY_DIR/nginx.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/ubuntu/trade_manthan_web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Create setup script for EC2
cat > $DEPLOY_DIR/setup_ec2.sh << 'EOF'
#!/bin/bash

set -e

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y python3 python3-pip python3-venv nginx git curl

# Create application directory
echo "Creating application directory..."
mkdir -p /home/ubuntu/trade_manthan_web
cd /home/ubuntu/trade_manthan_web

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up nginx
echo "Setting up nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/trade-manthan-web
sudo ln -sf /etc/nginx/sites-available/trade-manthan-web /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Set up systemd service
echo "Setting up systemd service..."
sudo cp trade-manthan-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trade-manthan-web

# Set proper permissions
echo "Setting permissions..."
sudo chown -R ubuntu:ubuntu /home/ubuntu/trade_manthan_web
chmod +x /home/ubuntu/trade_manthan_web/start_app.py

# Create log directory
mkdir -p /home/ubuntu/trade_manthan_web/logs

echo "EC2 setup completed successfully!"
echo "Please configure your environment variables and start the service."
EOF

chmod +x $DEPLOY_DIR/setup_ec2.sh

# Create environment configuration script
cat > $DEPLOY_DIR/configure_env.sh << 'EOF'
#!/bin/bash

# This script helps configure environment variables
echo "Trade Manthan Web Application Environment Configuration"
echo "======================================================"
echo ""

# Get Google OAuth credentials
read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
read -s -p "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
echo ""
read -p "Enter your domain (e.g., yourdomain.com): " DOMAIN
read -s -p "Enter a strong secret key for Flask: " FLASK_SECRET_KEY
echo ""

# Update service file
sudo sed -i "s/your-google-client-id/$GOOGLE_CLIENT_ID/g" /etc/systemd/system/trade-manthan-web.service
sudo sed -i "s/your-google-client-secret/$GOOGLE_CLIENT_SECRET/g" /etc/systemd/system/trade-manthan-web.service
sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/systemd/system/trade-manthan-web.service
sudo sed -i "s|your-production-secret-key-change-this|$FLASK_SECRET_KEY|g" /etc/systemd/system/trade-manthan-web.service

# Update nginx configuration
sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/trade-manthan-web

# Reload systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl start trade-manthan-web

echo "Environment configured successfully!"
echo "Application should now be running at: https://$DOMAIN"
EOF

chmod +x $DEPLOY_DIR/configure_env.sh

# Create SSL setup script
cat > $DEPLOY_DIR/setup_ssl.sh << 'EOF'
#!/bin/bash

# Install Certbot for SSL certificates
sudo apt-get install -y certbot python3-certbot-nginx

# Get domain from user
read -p "Enter your domain (e.g., yourdomain.com): " DOMAIN

# Obtain SSL certificate
sudo certbot --nginx -d $DOMAIN

# Set up auto-renewal
sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

echo "SSL certificate installed successfully!"
echo "Your application is now available at: https://$DOMAIN"
EOF

chmod +x $DEPLOY_DIR/setup_ssl.sh

# Create monitoring script
cat > $DEPLOY_DIR/monitor.sh << 'EOF'
#!/bin/bash

echo "Trade Manthan Web Application Status"
echo "==================================="
echo ""

echo "Service Status:"
sudo systemctl status trade-manthan-web --no-pager -l

echo ""
echo "Nginx Status:"
sudo systemctl status nginx --no-pager -l

echo ""
echo "Recent Logs:"
sudo journalctl -u trade-manthan-web -n 20 --no-pager

echo ""
echo "Disk Usage:"
df -h

echo ""
echo "Memory Usage:"
free -h
EOF

chmod +x $DEPLOY_DIR/monitor.sh

# Create backup script
cat > $DEPLOY_DIR/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
if [ -f "/home/ubuntu/trade_manthan_web/users.db" ]; then
    cp /home/ubuntu/trade_manthan_web/users.db $BACKUP_DIR/users_$DATE.db
    echo "Database backed up to: $BACKUP_DIR/users_$DATE.db"
fi

# Backup logs
if [ -d "/home/ubuntu/trade_manthan_web/logs" ]; then
    tar -czf $BACKUP_DIR/logs_$DATE.tar.gz -C /home/ubuntu/trade_manthan_web logs/
    echo "Logs backed up to: $BACKUP_DIR/logs_$DATE.tar.gz"
fi

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed successfully!"
EOF

chmod +x $DEPLOY_DIR/backup.sh

# Create README for deployment
cat > $DEPLOY_DIR/README_DEPLOYMENT.md << 'EOF'
# Trade Manthan Web Application - EC2 Deployment

## Quick Start

1. **Run the setup script:**
   ```bash
   ./setup_ec2.sh
   ```

2. **Configure environment variables:**
   ```bash
   ./configure_env.sh
   ```

3. **Set up SSL (optional but recommended):**
   ```bash
   ./setup_ssl.sh
   ```

## Management Commands

### Check application status:
```bash
./monitor.sh
```

### Restart application:
```bash
sudo systemctl restart trade-manthan-web
```

### View logs:
```bash
sudo journalctl -u trade-manthan-web -f
```

### Backup data:
```bash
./backup.sh
```

## Important Notes

- Make sure to configure your Google OAuth credentials
- Update the domain in nginx configuration
- Set a strong Flask secret key
- Configure firewall to allow HTTP (80) and HTTPS (443) traffic
- Set up regular backups

## Troubleshooting

1. **Service won't start:** Check logs with `sudo journalctl -u trade-manthan-web`
2. **Nginx issues:** Check nginx status with `sudo nginx -t`
3. **Permission issues:** Ensure proper ownership with `sudo chown -R ubuntu:ubuntu /home/ubuntu/trade_manthan_web`
EOF

# Create deployment package
tar -czf trade_manthan_web_deploy.tar.gz $DEPLOY_DIR/

print_success "Deployment package created: trade_manthan_web_deploy.tar.gz"

# Upload to EC2
print_status "Uploading deployment package to EC2..."
scp -i "$EC2_KEY_PATH" -o StrictHostKeyChecking=no trade_manthan_web_deploy.tar.gz $EC2_USER@$EC2_HOST:~/

# Execute setup on EC2
print_status "Setting up application on EC2..."
ssh -i "$EC2_KEY_PATH" -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST << 'ENDSSH'
    # Extract deployment package
    tar -xzf trade_manthan_web_deploy.tar.gz
    cd deploy_package
    
    # Run setup script
    ./setup_ec2.sh
    
    echo "Setup completed! Please run ./configure_env.sh to configure your environment variables."
ENDSSH

print_success "Deployment completed successfully!"
print_status "Next steps:"
echo "1. SSH into your EC2 instance: ssh -i $EC2_KEY_PATH $EC2_USER@$EC2_HOST"
echo "2. Navigate to: cd deploy_package"
echo "3. Configure environment: ./configure_env.sh"
echo "4. Set up SSL (optional): ./setup_ssl.sh"
echo "5. Monitor application: ./monitor.sh"

# Clean up local files
rm -rf $DEPLOY_DIR
rm trade_manthan_web_deploy.tar.gz

print_success "Local cleanup completed!"
