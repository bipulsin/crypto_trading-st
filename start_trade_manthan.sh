#!/bin/bash

# Trade Manthan Startup Script
# This script handles OAuth configuration, environment setup, and server startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Trade Manthan"
DOMAIN="trademanthan.in"
SERVICE_NAME="trade-manthan-web"
APP_DIR="/home/ubuntu/trade_manthan_web"
LOG_FILE="/var/log/trade-manthan-startup.log"

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

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a "$LOG_FILE"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if running on EC2
    if ! curl -s http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; then
        print_warning "Not running on EC2 instance"
    else
        print_success "Running on EC2 instance"
    fi
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        print_error "Nginx is not installed. Please install nginx first."
        exit 1
    fi
    
    # Check if systemctl is available
    if ! command -v systemctl &> /dev/null; then
        print_error "Systemctl is not available. This script requires systemd."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup OAuth configuration
setup_oauth() {
    print_status "Setting up OAuth configuration..."
    
    # Check if OAuth credentials are already configured
    if [[ -f "$APP_DIR/.env" ]] && grep -q "GOOGLE_CLIENT_ID" "$APP_DIR/.env"; then
        print_status "OAuth credentials found in .env file"
        return 0
    fi
    
    # Check if environment variables are set
    if [[ -n "$GOOGLE_CLIENT_ID" ]] && [[ -n "$GOOGLE_CLIENT_SECRET" ]]; then
        print_status "OAuth credentials found in environment variables"
        return 0
    fi
    
    # Prompt for OAuth credentials
    print_warning "OAuth credentials not found. Please provide them:"
    echo
    
    read -p "Enter your Google Client ID: " GOOGLE_CLIENT_ID
    read -s -p "Enter your Google Client Secret: " GOOGLE_CLIENT_SECRET
    echo
    
    if [[ -z "$GOOGLE_CLIENT_ID" ]] || [[ -z "$GOOGLE_CLIENT_SECRET" ]]; then
        print_error "OAuth credentials cannot be empty"
        exit 1
    fi
    
    # Create/update .env file
    cat > "$APP_DIR/.env" << EOF
# Trade Manthan Environment Configuration
STRATEGY_CANDLE_SIZE=15m
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI=https://$DOMAIN/callback
FLASK_SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production
EOF
    
    print_success "OAuth configuration saved to .env file"
}

# Function to update systemd service
update_systemd_service() {
    print_status "Updating systemd service configuration..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Trade Manthan Web Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=FLASK_ENV=production
Environment=FLASK_SECRET_KEY=$(grep FLASK_SECRET_KEY "$APP_DIR/.env" | cut -d'=' -f2)
Environment=GOOGLE_CLIENT_ID=$(grep GOOGLE_CLIENT_ID "$APP_DIR/.env" | cut -d'=' -f2)
Environment=GOOGLE_CLIENT_SECRET=$(grep GOOGLE_CLIENT_SECRET "$APP_DIR/.env" | cut -d'=' -f2)
Environment=GOOGLE_REDIRECT_URI=https://$DOMAIN/callback
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    
    print_success "Systemd service updated and enabled"
}

# Function to setup SSL certificate
setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    # Check if SSL certificate already exists
    if sudo certbot certificates | grep -q "$DOMAIN"; then
        print_status "SSL certificate already exists"
        return 0
    fi
    
    # Install certbot if not installed
    if ! command -v certbot &> /dev/null; then
        print_status "Installing certbot..."
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    fi
    
    # Obtain SSL certificate
    print_status "Obtaining SSL certificate for $DOMAIN..."
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"
    
    print_success "SSL certificate obtained successfully"
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start the web application
    sudo systemctl start $SERVICE_NAME
    
    # Check service status
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_success "$SERVICE_NAME service started successfully"
    else
        print_error "Failed to start $SERVICE_NAME service"
        sudo systemctl status $SERVICE_NAME --no-pager
        exit 1
    fi
    
    # Reload nginx
    sudo systemctl reload nginx
    
    print_success "All services started successfully"
}

# Function to verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check if web application is responding
    sleep 5  # Wait for service to fully start
    
    if curl -s -f "http://localhost:5000" > /dev/null 2>&1; then
        print_success "Web application is responding on port 5000"
    else
        print_error "Web application is not responding on port 5000"
        return 1
    fi
    
    # Check if HTTPS is working
    if curl -s -f "https://$DOMAIN" > /dev/null 2>&1; then
        print_success "HTTPS is working for $DOMAIN"
    else
        print_warning "HTTPS is not working for $DOMAIN"
        return 1
    fi
    
    # Check service status
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        print_success "$SERVICE_NAME service is running"
    else
        print_error "$SERVICE_NAME service is not running"
        return 1
    fi
    
    print_success "Setup verification completed successfully"
}

# Function to show status
show_status() {
    print_status "Current service status:"
    echo
    
    # Service status
    sudo systemctl status $SERVICE_NAME --no-pager | head -20
    echo
    
    # Port status
    echo "Port status:"
    sudo ss -tlnp | grep -E ":(80|443|5000)" || echo "No ports found"
    echo
    
    # SSL certificate status
    echo "SSL certificate status:"
    sudo certbot certificates 2>/dev/null | grep -A 5 "$DOMAIN" || echo "No SSL certificate found"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    sudo systemctl stop $SERVICE_NAME
    sudo systemctl reload nginx
    
    print_success "Services stopped successfully"
}

# Function to restart services
restart_services() {
    print_status "Restarting services..."
    
    sudo systemctl restart $SERVICE_NAME
    sudo systemctl reload nginx
    
    print_success "Services restarted successfully"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  start       Start all services (default)"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  status      Show current service status"
    echo "  setup       Setup OAuth and SSL (first time only)"
    echo "  verify      Verify current setup"
    echo "  help        Show this help message"
    echo
    echo "Examples:"
    echo "  $0           # Start services (default)"
    echo "  $0 setup     # First time setup"
    echo "  $0 status    # Check status"
    echo "  $0 restart   # Restart services"
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            check_root
            check_prerequisites
            setup_oauth
            update_systemd_service
            setup_ssl
            start_services
            verify_setup
            print_success "$APP_NAME is now running!"
            print_status "Access your application at: https://$DOMAIN"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            show_status
            ;;
        "setup")
            check_root
            check_prerequisites
            setup_oauth
            update_systemd_service
            setup_ssl
            print_success "Setup completed successfully!"
            ;;
        "verify")
            verify_setup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
