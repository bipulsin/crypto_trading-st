#!/usr/bin/env python3

import os
import sys
from app import app, init_db

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Set environment variables for Google OAuth (you'll need to set these)
    if not os.environ.get('GOOGLE_CLIENT_ID'):
        print("Warning: GOOGLE_CLIENT_ID not set. Please set your Google OAuth credentials.")
        print("You can get them from: https://console.developers.google.com/")
        print("For development, you can set dummy values:")
        os.environ['GOOGLE_CLIENT_ID'] = 'your-google-client-id'
        os.environ['GOOGLE_CLIENT_SECRET'] = 'your-google-client-secret'
        os.environ['GOOGLE_REDIRECT_URI'] = 'http://localhost:5000/callback'
    
    # Set Flask secret key
    if not os.environ.get('FLASK_SECRET_KEY'):
        os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    print("Starting Trade Manthan Web Application...")
    print("Access the application at: http://localhost:5000")
    print("Note: You need to configure Google OAuth for full functionality.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
