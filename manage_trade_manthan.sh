#!/bin/bash

# Trade Manthan Server Management Script
# This script provides comprehensive management of the Trade Manthan application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Trade Manthan"
DOMAIN="trademanthan.in"
SERVICE_NAME="trade-manthan-web"
EC2_HOST="13.115.183.85"
EC2_USER="ubuntu"
KEY_FILE="trademanthan.pem"
APP_DIR="/home/ubuntu/trade_manthan_web"

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

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    if [[ ! -f "$KEY_FILE" ]]; then
        print_error "SSH key file '$KEY_FILE' not found!"
        exit 1
    fi
    
    if ! command -v ssh &> /dev/null; then
        print_error "SSH client not found!"
        exit 1
    fi
    
    if ! command -v scp &> /dev/null; then
        print_error "SCP client not found!"
        exit 1
    fi
}

# Function to show server status
show_status() {
    print_header "=== Trade Manthan Server Status ==="
    
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
echo "=== Service Status ==="
sudo systemctl status trade-manthan-web --no-pager | head -15

echo -e "\n=== Port Status ==="
sudo ss -tlnp | grep -E ":(80|443|5000)" || echo "No ports found"

echo -e "\n=== SSL Certificate Status ==="
sudo certbot certificates 2>/dev/null | grep -A 5 "trademanthan.in" || echo "No SSL certificate found"

echo -e "\n=== Application Logs (Last 10 lines) ==="
sudo journalctl -u trade-manthan-web -n 10 --no-pager

echo -e "\n=== Disk Usage ==="
df -h /home/ubuntu/trade_manthan_web

echo -e "\n=== Memory Usage ==="
free -h
EOF
}

# Function to start the server
start_server() {
    print_header "=== Starting Trade Manthan Server ==="
    
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
sudo systemctl start trade-manthan-web
sudo systemctl reload nginx

echo "Service status:"
sudo systemctl status trade-manthan-web --no-pager | head -10
EOF
    
    print_success "Server started successfully!"
}

# Function to stop the server
stop_server() {
    print_header "=== Stopping Trade Manthan Server ==="
    
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
sudo systemctl stop trade-manthan-web
sudo systemctl reload nginx

echo "Service status:"
sudo systemctl status trade-manthan-web --no-pager | head -5
EOF
    
    print_success "Server stopped successfully!"
}

# Function to restart the server
restart_server() {
    print_header "=== Restarting Trade Manthan Server ==="
    
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
sudo systemctl restart trade-manthan-web
sudo systemctl reload nginx

echo "Service status:"
sudo systemctl status trade-manthan-web --no-pager | head -10
EOF
    
    print_success "Server restarted successfully!"
}

# Function to deploy updates
deploy_updates() {
    print_header "=== Deploying Updates to EC2 ==="
    
    print_status "Pulling latest changes from Git..."
    git pull origin main
    
    print_status "Deploying to EC2 server..."
    ./deploy_to_ec2.sh
    
    print_success "Deployment completed successfully!"
}

# Function to check website health
check_health() {
    print_header "=== Website Health Check ==="
    
    print_status "Checking HTTP response..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN")
    echo "HTTP Status: $HTTP_STATUS"
    
    print_status "Checking HTTPS response..."
    HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN")
    echo "HTTPS Status: $HTTPS_STATUS"
    
    print_status "Checking login page..."
    LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/login")
    echo "Login Page Status: $LOGIN_STATUS"
    
    if [[ "$HTTPS_STATUS" == "302" ]] && [[ "$LOGIN_STATUS" == "200" ]]; then
        print_success "Website is healthy and responding correctly!"
    else
        print_warning "Website may have issues. Check the status above."
    fi
}

# Function to view logs
view_logs() {
    print_header "=== Viewing Application Logs ==="
    
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
echo "=== Recent Application Logs ==="
sudo journalctl -u trade-manthan-web -n 50 --no-pager

echo -e "\n=== Recent Nginx Logs ==="
sudo tail -n 20 /var/log/nginx/access.log

echo -e "\n=== Recent Error Logs ==="
sudo tail -n 20 /var/log/nginx/error.log
EOF
}

# Function to setup OAuth
setup_oauth() {
    print_header "=== Setting up OAuth Credentials ==="
    
    print_status "Running OAuth setup script..."
    ./setup_oauth.sh
}

# Function to quick fix OAuth
quick_fix_oauth() {
    print_header "=== Quick OAuth Fix ==="
    
    print_status "Applying quick OAuth fix..."
    ./quick_oauth_fix.sh
}

# Function to backup configuration
backup_config() {
    print_header "=== Backing up Configuration ==="
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    print_status "Creating backup in $BACKUP_DIR..."
    
    # Backup local files
    cp .env "$BACKUP_DIR/" 2>/dev/null || echo "No local .env file"
    cp oauth_config.py "$BACKUP_DIR/" 2>/dev/null || echo "No oauth_config.py file"
    
    # Backup EC2 configuration
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << EOF
mkdir -p /tmp/trade_manthan_backup
cp $APP_DIR/.env /tmp/trade_manthan_backup/ 2>/dev/null || echo "No .env file on EC2"
cp /etc/systemd/system/$SERVICE_NAME.service /tmp/trade_manthan_backup/ 2>/dev/null || echo "No service file"
EOF
    
    scp -i "$KEY_FILE" -r "$EC2_USER@$EC2_HOST:/tmp/trade_manthan_backup/*" "$BACKUP_DIR/" 2>/dev/null || echo "No EC2 files to backup"
    
    print_success "Backup created in $BACKUP_DIR"
}

# Function to restore configuration
restore_config() {
    print_header "=== Restoring Configuration ==="
    
    if [[ -z "$1" ]]; then
        print_error "Please specify backup directory to restore from"
        echo "Usage: $0 restore <backup_directory>"
        exit 1
    fi
    
    BACKUP_DIR="$1"
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        print_error "Backup directory '$BACKUP_DIR' not found!"
        exit 1
    fi
    
    print_status "Restoring from backup: $BACKUP_DIR"
    
    # Restore local files
    if [[ -f "$BACKUP_DIR/.env" ]]; then
        cp "$BACKUP_DIR/.env" .env
        print_success "Restored local .env file"
    fi
    
    # Restore EC2 configuration
    if [[ -f "$BACKUP_DIR/trade-manthan-web.service" ]]; then
        scp -i "$KEY_FILE" "$BACKUP_DIR/trade-manthan-web.service" "$EC2_USER@$EC2_HOST:/tmp/"
        
        ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
sudo cp /tmp/trade-manthan-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart trade-manthan-web
EOF
        
        print_success "Restored EC2 service configuration"
    fi
    
    print_success "Configuration restored successfully!"
}

# Function to show help
show_help() {
    print_header "=== Trade Manthan Server Management Script ==="
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  status              Show server status and health"
    echo "  start               Start the server"
    echo "  stop                Stop the server"
    echo "  restart             Restart the server"
    echo "  deploy              Deploy latest updates to EC2"
    echo "  health              Check website health"
    echo "  logs                View application logs"
    echo "  oauth-setup         Set up OAuth credentials"
    echo "  oauth-fix           Apply quick OAuth fix"
    echo "  backup              Backup current configuration"
    echo "  restore <dir>       Restore configuration from backup"
    echo "  help                Show this help message"
    echo
    echo "Examples:"
    echo "  $0 status           # Check server status"
    echo "  $0 restart          # Restart the server"
    echo "  $0 deploy           # Deploy updates"
    echo "  $0 oauth-setup      # Set up OAuth"
    echo "  $0 backup           # Create backup"
    echo "  $0 restore backup_20250810_120000  # Restore from backup"
    echo
    echo "Note: Make sure you have the SSH key file '$KEY_FILE' in the current directory"
}

# Main execution
main() {
    check_prerequisites
    
    case "${1:-help}" in
        "status")
            show_status
            ;;
        "start")
            start_server
            ;;
        "stop")
            stop_server
            ;;
        "restart")
            restart_server
            ;;
        "deploy")
            deploy_updates
            ;;
        "health")
            check_health
            ;;
        "logs")
            view_logs
            ;;
        "oauth-setup")
            setup_oauth
            ;;
        "oauth-fix")
            quick_fix_oauth
            ;;
        "backup")
            backup_config
            ;;
        "restore")
            restore_config "$2"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
