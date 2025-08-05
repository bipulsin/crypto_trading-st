# 🚀 EC2 Deployment Guide for Web Configuration Server

This guide will help you deploy the web configuration server on your EC2 instance with IP `43.206.219.70`.

## 📋 Prerequisites

- EC2 instance running Ubuntu/Linux
- SSH access to your EC2 instance
- Python 3.7+ installed
- Git installed

## 🔧 Step-by-Step Deployment

### **Step 1: Connect to Your EC2 Instance**

```bash
# Connect via SSH (replace with your key file)
ssh -i your-key.pem ubuntu@43.206.219.70
```

### **Step 2: Update System and Install Dependencies**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Check Python version (should be 3.10.2)
python3 --version

# Install Git and Nginx
sudo apt install git nginx -y
```

### **Step 3: Set Up Project Directory**

```bash
# Check current directory
pwd

# Choose directory structure:
# Option 1: Use current root directory (if files are already there)
# Option 2: Move to ~/trading-bot directory (recommended)
# Option 3: Create new ~/trading-bot directory

# For Option 2 (recommended):
mkdir -p ~/trading-bot
cd ~/trading-bot

# Clone your repository
git clone https://github.com/bipulsin/crypto_trading-st.git
cd crypto_trading-st

# Create or activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi
```

### **Step 4: Install Python Dependencies**

```bash
# Verify Python version
python3 --version

# Install dependencies
pip install -r requirements.txt

# Verify virtual environment
echo $VIRTUAL_ENV
```

### **Step 5: Configure Security**

#### **A. Set Environment Variables**

```bash
# Create environment file
cat > .env << EOF
WEB_CONFIG_USERNAME=your_username
WEB_CONFIG_PASSWORD=your_secure_password
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
WEB_CONFIG_PORT=5000
EOF

# Load environment variables
export $(cat .env | xargs)
```

#### **B. Configure EC2 Security Group**

1. Go to AWS Console → EC2 → Security Groups
2. Select your EC2 instance's security group
3. Add inbound rules:

| Type | Port | Source | Description |
|------|------|--------|-------------|
| HTTP | 80 | 0.0.0.0/0 | HTTP access |
| HTTPS | 443 | 0.0.0.0/0 | HTTPS access |
| Custom TCP | 5000 | 0.0.0.0/0 | Web config server |
| SSH | 22 | Your IP | SSH access |

### **Step 6: Start the Production Server**

```bash
# Make script executable
chmod +x start_production_server.py

# Start production server
python3 start_production_server.py
```

Choose option 1 (Gunicorn) for production deployment.

**Note**: The deployment script will automatically detect your current directory and Python setup, and create the systemd service with the correct paths.

### **Step 7: Test the Deployment**

Open your browser and navigate to:
- **Dashboard**: http://43.206.219.70:5000
- **API**: http://43.206.219.70:5000/api/config

Login with:
- Username: `your_username`
- Password: `your_secure_password`

## 🔒 Security Enhancements

### **A. Set Up Nginx Reverse Proxy (Recommended)**

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/trading-bot-config << EOF
server {
    listen 80;
    server_name 43.206.219.70;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/trading-bot-config /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### **B. Set Up SSL with Let's Encrypt**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **C. Configure Firewall (UFW)**

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow web config port (if not using Nginx)
sudo ufw allow 5000

# Check status
sudo ufw status
```

## 🚀 Production Deployment Options

### **Option 1: Systemd Service (Recommended)**

```bash
# Create systemd service
sudo cp trading-bot-web-config.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot-web-config
sudo systemctl start trading-bot-web-config

# Check status
sudo systemctl status trading-bot-web-config

# View logs
sudo journalctl -u trading-bot-web-config -f
```

### **Option 2: Screen Session**

```bash
# Install screen
sudo apt install screen -y

# Create screen session
screen -S trading-bot-config

# Start server
python3 start_production_server.py

# Detach from screen: Ctrl+A, then D
# Reattach: screen -r trading-bot-config
```

### **Option 3: PM2 (Alternative)**

```bash
# Install Node.js and PM2
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PM2
sudo npm install -g pm2

# Start with PM2
pm2 start web_config.py --name trading-bot-config --interpreter python3
pm2 startup
pm2 save
```

## 📊 Monitoring and Logs

### **View Application Logs**

```bash
# If using systemd
sudo journalctl -u trading-bot-web-config -f

# If using Gunicorn directly
tail -f gunicorn.log

# If using PM2
pm2 logs trading-bot-config
```

### **Monitor System Resources**

```bash
# Check CPU and memory usage
htop

# Check disk usage
df -h

# Check network connections
netstat -tulpn | grep :5000
```

## 🔧 Troubleshooting

### **Common Issues**

#### **1. Port Already in Use**
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>
```

#### **2. Permission Denied**
```bash
# Fix file permissions
chmod +x *.py
chmod 644 config.py
```

#### **3. Module Not Found**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### **4. Connection Refused**
```bash
# Check if server is running
ps aux | grep python

# Check firewall
sudo ufw status

# Check security group rules in AWS console
```

### **Debug Mode**

```bash
# Start in debug mode
export FLASK_ENV=development
python3 web_config.py --debug
```

## 🔄 Updates and Maintenance

### **Update Application**

```bash
# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart trading-bot-web-config

# Or if using PM2
pm2 restart trading-bot-config
```

### **Backup Configuration**

```bash
# Create backup
cp config.py config_backup_$(date +%Y%m%d_%H%M%S).py

# Restore from backup
cp config_backup_YYYYMMDD_HHMMSS.py config.py
```

## 📱 Access URLs

After deployment, you can access:

- **Main Dashboard**: http://43.206.219.70:5000
- **API Endpoints**: http://43.206.219.70:5000/api/
- **Configuration**: http://43.206.219.70:5000/api/config
- **Backups**: http://43.206.219.70:5000/api/backups

## 🔐 Security Checklist

- [ ] Changed default username/password
- [ ] Set up SSL certificate
- [ ] Configured firewall
- [ ] Set up Nginx reverse proxy
- [ ] Enabled automatic backups
- [ ] Set up monitoring
- [ ] Configured rate limiting
- [ ] Set up systemd service
- [ ] Tested all functionality

## 🆘 Support

If you encounter issues:

1. Check the logs: `sudo journalctl -u trading-bot-web-config -f`
2. Verify network connectivity: `curl http://localhost:5000`
3. Check service status: `sudo systemctl status trading-bot-web-config`
4. Review security group settings in AWS console
5. Test with debug mode enabled

## 🎯 Next Steps

1. **Set up monitoring** with tools like CloudWatch
2. **Configure alerts** for system issues
3. **Set up automated backups** to S3
4. **Implement logging** to CloudWatch Logs
5. **Set up CI/CD** pipeline for updates 