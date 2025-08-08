#!/bin/bash

# Local Development Setup Script for Trade Manthan Web Application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "Setting up Trade Manthan Web Application for local development..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "Python version: $PYTHON_VERSION"

# Create virtual environment
print_status "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Removing..."
    rm -rf venv
fi

python3 -m venv venv
print_success "Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p static
mkdir -p config_backups

# Copy logo if it exists
if [ -f "logo.jpg" ]; then
    cp logo.jpg static/
    print_success "Logo copied to static directory"
else
    print_warning "logo.jpg not found. Please add it to the static directory manually."
fi

# Create .env file template
print_status "Creating environment file template..."
cat > .env.template << 'EOF'
# Trade Manthan Web Application Environment Variables
# Copy this file to .env and fill in your values

# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-change-this-in-production
FLASK_ENV=development

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback

# Database Configuration (for production)
# DATABASE_URL=postgresql://user:password@localhost/trade_manthan

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.template .env
    print_success "Environment file created (.env)"
    print_warning "Please edit .env file with your actual values"
else
    print_status "Environment file already exists (.env)"
fi

# Create a simple run script
cat > run_local.sh << 'EOF'
#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
python3 start_app.py
EOF

chmod +x run_local.sh

# Create a test script
cat > test_app.py << 'EOF'
#!/usr/bin/env python3

import requests
import time

def test_app():
    """Simple test to check if the app is running"""
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        if response.status_code == 200:
            print("✅ Application is running successfully!")
            return True
        else:
            print(f"❌ Application returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Application is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error testing application: {e}")
        return False

if __name__ == "__main__":
    print("Testing Trade Manthan Web Application...")
    time.sleep(2)  # Give the app time to start
    test_app()
EOF

print_success "Local development setup completed!"
echo ""
print_status "Next steps:"
echo ""
echo "1. Configure Google OAuth (optional for testing):"
echo "   - Go to https://console.developers.google.com/"
echo "   - Create a new project"
echo "   - Enable Google+ API"
echo "   - Create OAuth 2.0 credentials"
echo "   - Set redirect URI to: http://localhost:5000/callback"
echo ""
echo "2. Update environment variables:"
echo "   - Edit .env file with your Google OAuth credentials"
echo "   - Set a strong Flask secret key"
echo ""
echo "3. Run the application:"
echo "   ./run_local.sh"
echo "   or"
echo "   python3 start_app.py"
echo ""
echo "4. Access the application:"
echo "   http://localhost:5000"
echo ""
echo "5. Test the application:"
echo "   python3 test_app.py"
echo ""
print_warning "Note: For full functionality, you need to configure Google OAuth."
print_warning "Without OAuth, you can still test the basic structure."
