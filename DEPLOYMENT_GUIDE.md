# 🚀 React Frontend Deployment Guide to EC2

This guide will walk you through deploying your React frontend to an EC2 server with all the necessary configurations and optimizations.

## 📋 Prerequisites

- **EC2 Instance** running Ubuntu 20.04+ or Amazon Linux 2
- **SSH Access** to your EC2 instance
- **Domain Name** (optional but recommended for SSL)
- **Local Development Environment** with Node.js and npm

## 🔧 Step 1: Prepare Your Local Environment

### 1.1 Install Dependencies
```bash
# Navigate to your project directory
cd crypto_trading_1

# Install dependencies
npm install

# Verify everything works locally
npm start
```

### 1.2 Update Production Configuration
```bash
# Copy the deployment configuration
cp deployment.config .env.production

# Edit .env.production with your actual values
nano .env.production
```

**Required Updates in `.env.production`:**
```env
REACT_APP_API_URL=https://your-ec2-domain.com
# or if no domain: REACT_APP_API_URL=http://your-ec2-ip
```

## 🖥️ Step 2: Prepare Your EC2 Server

### 2.1 Connect to Your EC2 Instance
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 2.2 Run the EC2 Setup Script
```bash
# Download the setup script
wget https://raw.githubusercontent.com/your-repo/crypto_trading_1/main/setup_ec2_for_react.sh

# Make it executable
chmod +x setup_ec2_for_react.sh

# Run the setup
./setup_ec2_for_react.sh
```

**What this script does:**
- ✅ Installs Nginx web server
- ✅ Installs Node.js and PM2
- ✅ Configures firewall rules
- ✅ Sets up Nginx configuration for React
- ✅ Creates deployment helper scripts
- ✅ Sets up log rotation
- ✅ Creates systemd service for Python backend

### 2.3 Verify Setup
```bash
# Check nginx status
sudo systemctl status nginx

# Check if the site is configured
sudo nginx -t

# Check the created files
ls -la
```

## 🚀 Step 3: Deploy Your React Frontend

### 3.1 Build Your React App
```bash
# On your local machine
npm run build

# Verify build was created
ls -la build/
```

### 3.2 Deploy Using the Quick Script

**Option A: Quick Deployment (Recommended)**
```bash
# Update the configuration in quick_deploy_react.sh
nano quick_deploy_react.sh

# Make it executable
chmod +x quick_deploy_react.sh

# Run deployment
./quick_deploy_react.sh
```

**Option B: Manual Deployment**
```bash
# Create deployment package
tar -czf react-frontend-$(date +%Y%m%d-%H%M%S).tar.gz build/

# Upload to EC2
scp -i your-key.pem react-frontend-*.tar.gz ubuntu@your-ec2-ip:/tmp/

# SSH to EC2 and deploy
ssh -i your-key.pem ubuntu@your-ec2-ip
cd /tmp
sudo tar -xzf react-frontend-*.tar.gz -C /var/www/trademanthan-frontend
sudo mv /var/www/trademanthan-frontend/build/* /var/www/trademanthan-frontend/
sudo chown -R www-data:www-data /var/www/trademanthan-frontend
sudo systemctl reload nginx
```

## 🔒 Step 4: Set Up SSL Certificate (Optional but Recommended)

### 4.1 Install Certbot
```bash
# On your EC2 instance
sudo apt install certbot python3-certbot-nginx
```

### 4.2 Get SSL Certificate
```bash
# Replace with your actual domain and email
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --non-interactive --agree-tos --email your-email@example.com
```

### 4.3 Test Auto-Renewal
```bash
sudo certbot renew --dry-run
```

## 🧪 Step 5: Test Your Deployment

### 5.1 Health Check
```bash
# On your EC2 instance
./health-check.sh
```

### 5.2 Test Endpoints
```bash
# Test React app
curl http://localhost/health

# Test API proxy (if Python backend is running)
curl http://localhost/api/health

# Test from external
curl http://your-ec2-ip/health
```

### 5.3 Browser Testing
- Open `http://your-ec2-ip` in your browser
- Test all major functionality
- Check mobile responsiveness
- Verify API calls work

## 🔄 Step 6: Set Up Continuous Deployment

### 6.1 Create GitHub Actions Workflow
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy React Frontend to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Build React app
      run: npm run build
      env:
        REACT_APP_API_URL: ${{ secrets.REACT_APP_API_URL }}
    
    - name: Deploy to EC2
      uses: appleboy/scp-action@v0.1.4
      with:
        host: ${{ secrets.EC2_HOST }}
        username: ${{ secrets.EC2_USER }}
        key: ${{ secrets.EC2_SSH_KEY }}
        source: "build/*"
        target: "/tmp/react-deploy/"
    
    - name: Execute deployment script
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.EC2_HOST }}
        username: ${{ secrets.EC2_USER }}
        key: ${{ secrets.EC2_SSH_KEY }}
        script: |
          cd /tmp/react-deploy
          sudo cp -r * /var/www/trademanthan-frontend/
          sudo chown -R www-data:www-data /var/www/trademanthan-frontend
          sudo systemctl reload nginx
```

### 6.2 Set GitHub Secrets
- `EC2_HOST`: Your EC2 public IP or domain
- `EC2_USER`: Your EC2 username (usually `ubuntu`)
- `EC2_SSH_KEY`: Your private SSH key
- `REACT_APP_API_URL`: Your production API URL

## 🔧 Step 7: Monitor and Maintain

### 7.1 Check Logs
```bash
# Nginx access logs
sudo tail -f /var/log/nginx/trademanthan-frontend/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/trademanthan-frontend/error.log

# Application logs
tail -f /home/ubuntu/crypto_trading_1/logs/*.log
```

### 7.2 Performance Monitoring
```bash
# Check nginx status
sudo systemctl status nginx

# Check disk usage
df -h /var/www/trademanthan-frontend

# Check memory usage
free -h

# Check process status
pm2 status
```

### 7.3 Backup Strategy
```bash
# Create backup script
cat > backup-react.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups/react-frontend"
DATE=$(date +%Y%m%d-%H%M%S)
sudo mkdir -p "$BACKUP_DIR"
sudo cp -r /var/www/trademanthan-frontend "$BACKUP_DIR/frontend-$DATE"
echo "Backup created: $BACKUP_DIR/frontend-$DATE"
EOF

chmod +x backup-react.sh
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Nginx Not Starting
```bash
# Check configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Check if port 80 is in use
sudo netstat -tlnp | grep :80
```

#### 2. React App Not Loading
```bash
# Check file permissions
ls -la /var/www/trademanthan-frontend/

# Check nginx configuration
sudo nginx -t

# Check nginx status
sudo systemctl status nginx
```

#### 3. API Calls Failing
```bash
# Check if Python backend is running
curl http://localhost:5000/health

# Check firewall rules
sudo ufw status

# Check nginx proxy configuration
sudo cat /etc/nginx/sites-available/trademanthan-frontend
```

#### 4. SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check nginx SSL configuration
sudo nginx -t
```

## 📊 Performance Optimization

### 1. Enable Gzip Compression
Already configured in the nginx setup script.

### 2. Set Cache Headers
Already configured for static assets.

### 3. Enable HTTP/2
```bash
# Edit nginx configuration
sudo nano /etc/nginx/sites-available/trademanthan-frontend

# Add to server block:
listen 443 ssl http2;
```

### 4. Optimize Images
```bash
# Install image optimization tools
sudo apt install -y jpegoptim optipng

# Create optimization script
cat > optimize-images.sh << 'EOF'
#!/bin/bash
find /var/www/trademanthan-frontend -name "*.jpg" -exec jpegoptim --strip-all {} \;
find /var/www/trademanthan-frontend -name "*.png" -exec optipng -o5 {} \;
EOF
```

## 🔐 Security Considerations

### 1. Firewall Configuration
- Only allow necessary ports (22, 80, 443)
- Use security groups in AWS
- Regular security updates

### 2. SSL/TLS Configuration
- Use strong ciphers
- Enable HSTS
- Regular certificate renewal

### 3. Access Control
- Restrict nginx access to necessary directories
- Use proper file permissions
- Regular security audits

## 📈 Scaling Considerations

### 1. Load Balancer
- Use AWS Application Load Balancer
- Multiple EC2 instances
- Health checks and auto-scaling

### 2. CDN
- Use CloudFront for static assets
- Global distribution
- Reduced latency

### 3. Database
- Separate database instance
- Read replicas
- Connection pooling

## 🎯 Next Steps

1. **Monitor Performance**: Set up monitoring and alerting
2. **Automate Backups**: Schedule regular backups
3. **Set Up Logging**: Centralized logging solution
4. **Performance Testing**: Load testing and optimization
5. **Security Audits**: Regular security assessments

## 📞 Support

If you encounter issues:
1. Check the logs first
2. Review this deployment guide
3. Check nginx and system status
4. Verify file permissions and configurations

---

**🎉 Congratulations! Your React frontend is now deployed on EC2!**

Your application should be accessible at:
- **HTTP**: `http://your-ec2-ip`
- **HTTPS**: `https://your-domain.com` (if SSL is configured)
