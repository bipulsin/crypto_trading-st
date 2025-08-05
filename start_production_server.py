#!/usr/bin/env python3

"""
Production Web Configuration Server for EC2
===========================================

This script starts the web configuration server optimized for EC2 deployment
with security features and production settings.

Usage:
    python3 start_production_server.py

Environment Variables:
    WEB_CONFIG_USERNAME - Username for basic auth (default: admin)
    WEB_CONFIG_PASSWORD - Password for basic auth (default: admin123)
    FLASK_SECRET_KEY - Secret key for Flask sessions
    WEB_CONFIG_PORT - Port to run on (default: 5000)
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def setup_environment():
    """Setup environment variables for production"""
    # Set default values if not provided
    if not os.environ.get('WEB_CONFIG_USERNAME'):
        os.environ['WEB_CONFIG_USERNAME'] = 'admin'
    
    if not os.environ.get('WEB_CONFIG_PASSWORD'):
        os.environ['WEB_CONFIG_PASSWORD'] = 'admin123'
    
    if not os.environ.get('FLASK_SECRET_KEY'):
        # Generate a random secret key
        import secrets
        os.environ['FLASK_SECRET_KEY'] = secrets.token_hex(32)
    
    if not os.environ.get('WEB_CONFIG_PORT'):
        os.environ['WEB_CONFIG_PORT'] = '5000'

def check_dependencies():
    """Check and install required dependencies"""
    required_packages = ['flask', 'flask-cors', 'flask-limiter', 'pyopenssl', 'gunicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("📦 Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            return False
    
    return True

def create_systemd_service():
    """Create systemd service file for auto-start"""
    service_content = f"""[Unit]
Description=Trading Bot Web Configuration Server
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'ubuntu')}
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getenv('PATH')}
Environment=WEB_CONFIG_USERNAME={os.environ.get('WEB_CONFIG_USERNAME', 'admin')}
Environment=WEB_CONFIG_PASSWORD={os.environ.get('WEB_CONFIG_PASSWORD', 'admin123')}
Environment=FLASK_SECRET_KEY={os.environ.get('FLASK_SECRET_KEY')}
Environment=WEB_CONFIG_PORT={os.environ.get('WEB_CONFIG_PORT', '5000')}
ExecStart={sys.executable} web_config.py --host 0.0.0.0 --port {os.environ.get('WEB_CONFIG_PORT', '5000')}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = '/etc/systemd/system/trading-bot-web-config.service'
    
    try:
        with open('trading-bot-web-config.service', 'w') as f:
            f.write(service_content)
        
        print(f"📄 Systemd service file created: trading-bot-web-config.service")
        print(f"💡 To install as system service:")
        print(f"   sudo cp trading-bot-web-config.service {service_file}")
        print(f"   sudo systemctl daemon-reload")
        print(f"   sudo systemctl enable trading-bot-web-config")
        print(f"   sudo systemctl start trading-bot-web-config")
        
    except Exception as e:
        print(f"⚠️  Could not create service file: {e}")

def start_gunicorn():
    """Start server using Gunicorn for production"""
    port = os.environ.get('WEB_CONFIG_PORT', '5000')
    
    gunicorn_cmd = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '2',
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        'web_config:app'
    ]
    
    print("🚀 Starting production server with Gunicorn...")
    print(f"🌐 Server will be available at: http://43.206.219.70:{port}")
    print(f"🔧 API endpoints: http://43.206.219.70:{port}/api/")
    print(f"👤 Username: {os.environ.get('WEB_CONFIG_USERNAME', 'admin')}")
    print(f"🔑 Password: {os.environ.get('WEB_CONFIG_PASSWORD', 'admin123')}")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        subprocess.run(gunicorn_cmd)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def start_flask_dev():
    """Start server using Flask development server"""
    port = os.environ.get('WEB_CONFIG_PORT', '5000')
    
    print("🚀 Starting development server...")
    print(f"🌐 Server will be available at: http://43.206.219.70:{port}")
    print(f"🔧 API endpoints: http://43.206.219.70:{port}/api/")
    print(f"👤 Username: {os.environ.get('WEB_CONFIG_USERNAME', 'admin')}")
    print(f"🔑 Password: {os.environ.get('WEB_CONFIG_PASSWORD', 'admin123')}")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        from web_config import app
        app.run(host='0.0.0.0', port=int(port), debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    print("🤖 Trading Bot Web Configuration - Production Server")
    print("=" * 55)
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create systemd service file
    create_systemd_service()
    
    # Choose server type
    print("\n🔧 Choose server type:")
    print("1. Gunicorn (Production - Recommended)")
    print("2. Flask Development Server")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == '1':
        start_gunicorn()
    elif choice == '2':
        start_flask_dev()
    else:
        print("❌ Invalid choice. Using Gunicorn...")
        start_gunicorn()

if __name__ == '__main__':
    main() 