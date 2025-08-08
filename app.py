#!/usr/bin/env python3

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
import hashlib
import hmac
import time
import uuid

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')

# Configure CORS for production
CORS(app, origins=[
    'http://13.115.183.85',
    'http://13.115.183.85:5000',
    'https://13.115.183.85',
    'https://13.115.183.85:5000',
    'http://localhost:5000',
    'http://127.0.0.1:5000'
])

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/callback')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            google_id TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broker_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            connection_name TEXT NOT NULL,
            broker_id TEXT NOT NULL,
            broker_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            api_secret TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            leverage INTEGER DEFAULT 10,
            position_size_percent REAL DEFAULT 0.1,
            default_capital REAL DEFAULT 1000.0,
            max_capital_loss_percent REAL DEFAULT 5.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategy_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            broker_connection_id INTEGER,
            is_active BOOLEAN DEFAULT FALSE,
            config_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (broker_connection_id) REFERENCES broker_connections (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategy_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            is_running BOOLEAN DEFAULT FALSE,
            start_time TIMESTAMP,
            stop_time TIMESTAMP,
            pnl REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# User model
class User(UserMixin):
    def __init__(self, user_id, google_id, name, email, profile_picture):
        self.id = user_id
        self.google_id = google_id
        self.name = name
        self.email = email
        self.profile_picture = profile_picture

def generate_user_id():
    """Generate unique user ID in format TM99999"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return f"TM{count + 1:05d}"

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, google_id, name, email, profile_picture FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])
    return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/google-login')
def google_login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email']
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email']
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        google_id = id_info['sub']
        name = id_info['name']
        email = id_info['email']
        profile_picture = id_info.get('picture', '')
        
        # Check if user exists
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE google_id = ?', (google_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Update last login
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE google_id = ?', (google_id,))
            user_id = existing_user[0]
        else:
            # Create new user
            user_id = generate_user_id()
            cursor.execute('''
                INSERT INTO users (user_id, google_id, name, email, profile_picture)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, google_id, name, email, profile_picture))
            
            # Create default settings
            cursor.execute('''
                INSERT INTO user_settings (user_id, leverage, position_size_percent, default_capital, max_capital_loss_percent)
                VALUES (?, 10, 0.1, 1000.0, 5.0)
            ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        user = User(user_id, google_id, name, email, profile_picture)
        login_user(user)
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# API Routes
@app.route('/api/user/profile')
@login_required
def get_user_profile():
    return jsonify({
        'user_id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'profile_picture': current_user.profile_picture
    })

@app.route('/api/broker-connections', methods=['GET'])
@login_required
def get_broker_connections():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, connection_name, broker_id, broker_url, api_key, created_at
        FROM broker_connections WHERE user_id = ?
    ''', (current_user.id,))
    connections = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': row[0],
        'connection_name': row[1],
        'broker_id': row[2],
        'broker_url': row[3],
        'api_key': row[4][:10] + '...' if row[4] else '',  # Mask API key
        'created_at': row[5]
    } for row in connections])

@app.route('/api/broker-connections', methods=['POST'])
@login_required
def create_broker_connection():
    data = request.json
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO broker_connections (user_id, connection_name, broker_id, broker_url, api_key, api_secret)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user.id, data['connection_name'], data['broker_id'], data['broker_url'], data['api_key'], data['api_secret']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Broker connection created successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/user/settings', methods=['GET'])
@login_required
def get_user_settings():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT leverage, position_size_percent, default_capital, max_capital_loss_percent FROM user_settings WHERE user_id = ?', (current_user.id,))
    settings = cursor.fetchone()
    conn.close()
    
    if settings:
        return jsonify({
            'leverage': settings[0],
            'position_size_percent': settings[1],
            'default_capital': settings[2],
            'max_capital_loss_percent': settings[3]
        })
    return jsonify({})

@app.route('/api/user/settings', methods=['POST'])
@login_required
def update_user_settings():
    data = request.json
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE user_settings 
            SET leverage = ?, position_size_percent = ?, default_capital = ?, max_capital_loss_percent = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (data['leverage'], data['position_size_percent'], data['default_capital'], data['max_capital_loss_percent'], current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/strategy/supertrend/config', methods=['GET'])
@login_required
def get_supertrend_config():
    """Get SuperTrend strategy configuration for the current user"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT broker_connection_id, config_data, is_active
        FROM strategy_configs 
        WHERE user_id = ? AND strategy_name = 'supertrend'
        ORDER BY updated_at DESC LIMIT 1
    ''', (current_user.id,))
    config = cursor.fetchone()
    conn.close()
    
    if config:
        import json
        config_data = json.loads(config[1]) if config[1] else {}
        return jsonify({
            'broker_connection_id': config[0],
            'config_data': config_data,
            'is_active': bool(config[2])
        })
    return jsonify({})

@app.route('/api/strategy/supertrend/config', methods=['POST'])
@login_required
def save_supertrend_config():
    """Save SuperTrend strategy configuration"""
    data = request.json
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        import json
        config_data = json.dumps({
            'take_profit_multiplier': data.get('take_profit_multiplier', 2.0),
            'trailing_stop': data.get('trailing_stop', True),
            'candle_size': data.get('candle_size', '5m')
        })
        
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_configs 
            (user_id, strategy_name, broker_connection_id, config_data, is_active, updated_at)
            VALUES (?, 'supertrend', ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (current_user.id, data.get('broker_connection_id'), config_data, data.get('is_active', False)))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Strategy configuration saved successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/strategy/supertrend/status', methods=['GET'])
@login_required
def get_supertrend_status():
    """Get SuperTrend strategy status"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT is_running, start_time, stop_time, pnl, last_updated
        FROM strategy_status 
        WHERE user_id = ? AND strategy_name = 'supertrend'
        ORDER BY last_updated DESC LIMIT 1
    ''', (current_user.id,))
    status = cursor.fetchone()
    conn.close()
    
    if status:
        return jsonify({
            'is_running': bool(status[0]),
            'start_time': status[1],
            'stop_time': status[2],
            'pnl': float(status[3]),
            'last_updated': status[4]
        })
    else:
        return jsonify({
            'is_running': False,
            'start_time': None,
            'stop_time': None,
            'pnl': 0.0,
            'last_updated': datetime.now().isoformat()
        })

@app.route('/api/strategy/supertrend/toggle', methods=['POST'])
@login_required
def toggle_supertrend():
    """Toggle SuperTrend strategy on/off"""
    data = request.json
    is_running = data.get('is_running', False)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        if is_running:
            # Start strategy
            cursor.execute('''
                INSERT OR REPLACE INTO strategy_status 
                (user_id, strategy_name, is_running, start_time, last_updated)
                VALUES (?, 'supertrend', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (current_user.id,))
            
            # Update config to active
            cursor.execute('''
                UPDATE strategy_configs 
                SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND strategy_name = 'supertrend'
            ''', (current_user.id,))
        else:
            # Stop strategy
            cursor.execute('''
                INSERT OR REPLACE INTO strategy_status 
                (user_id, strategy_name, is_running, stop_time, last_updated)
                VALUES (?, 'supertrend', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (current_user.id,))
            
            # Update config to inactive
            cursor.execute('''
                UPDATE strategy_configs 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND strategy_name = 'supertrend'
            ''', (current_user.id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_running': is_running,
            'message': f'Strategy {"started" if is_running else "stopped"} successfully'
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/market/prices')
@login_required
def get_market_prices():
    # Mock market data - in real implementation, fetch from exchange
    return jsonify([
        {'symbol': 'BTC', 'name': 'Bitcoin', 'price': 45000.00},
        {'symbol': 'ETH', 'name': 'Ethereum', 'price': 3200.00},
        {'symbol': 'SOL', 'name': 'Solana', 'price': 95.50},
        {'symbol': 'DOGE', 'name': 'Dogecoin', 'price': 0.085}
    ])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
