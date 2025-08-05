#!/usr/bin/env python3

"""
Web Configuration Server Startup Script
=======================================

This script starts the web-based configuration interface for the trading bot.
It allows you to modify config.py variables through a web browser.

Usage:
    python3 start_web_config.py

Features:
- Web-based configuration dashboard
- Real-time validation
- Automatic backups
- Configuration restore functionality
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['flask', 'flask-cors']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Installing missing packages...")
        
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies. Please install manually:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
    
    return True

def check_files():
    """Check if required files exist"""
    required_files = [
        'web_config.py',
        'templates/config_dashboard.html',
        'config.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    return True

def start_server():
    """Start the web configuration server"""
    print("🌐 Starting Web Configuration Server...")
    print("=" * 50)
    
    # Check dependencies and files
    if not check_dependencies():
        return False
    
    if not check_files():
        return False
    
    print("✅ All checks passed!")
    print("\n🚀 Starting server...")
    
    # Start the web server
    try:
        # Import and run the web config server
        from web_config import app
        
        print("\n📱 Web Configuration Dashboard")
        print("=" * 30)
        print("🌐 Local URL: http://localhost:5000")
        print("🌐 Network URL: http://0.0.0.0:5000")
        print("🔧 API Endpoints: http://localhost:5000/api/")
        print("\n💡 The dashboard will open automatically in your browser.")
        print("   Press Ctrl+C to stop the server.")
        print("=" * 50)
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)
            try:
                webbrowser.open('http://localhost:5000')
            except:
                print("⚠️  Could not open browser automatically.")
                print("   Please open: http://localhost:5000")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Run the Flask app
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user.")
        return True
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        return False

def main():
    """Main function"""
    print("🤖 Trading Bot Web Configuration")
    print("=" * 40)
    print("This tool provides a web interface to configure your trading bot.")
    print("You can modify settings like leverage, position size, SuperTrend parameters, etc.")
    print()
    
    # Start the server
    success = start_server()
    
    if success:
        print("\n✅ Web configuration server stopped successfully.")
    else:
        print("\n❌ Failed to start web configuration server.")
        sys.exit(1)

if __name__ == '__main__':
    main() 