#!/usr/bin/env python3

import os
import json
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import config

app = Flask(__name__)
CORS(app)

# Configuration file path
CONFIG_FILE = 'config.py'
BACKUP_DIR = 'config_backups'

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def create_backup():
    """Create a backup of the current config file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'config_backup_{timestamp}.py')
    shutil.copy2(CONFIG_FILE, backup_file)
    return backup_file

def get_config_variables():
    """Extract all configurable variables from config.py"""
    config_vars = {}
    
    # Trading configuration
    config_vars['TRADING_FROM_LIVE'] = config.TRADING_FROM_LIVE
    config_vars['LEVERAGE'] = config.LEVERAGE
    config_vars['POSITION_SIZE_PERCENT'] = config.POSITION_SIZE_PERCENT
    config_vars['TAKE_PROFIT_MULTIPLIER'] = config.TAKE_PROFIT_MULTIPLIER
    config_vars['ST_WITH_TRAILING'] = config.ST_WITH_TRAILING
    
    # SuperTrend parameters
    config_vars['SUPERTREND_PERIOD'] = config.SUPERTREND_PERIOD
    config_vars['SUPERTREND_MULTIPLIER'] = config.SUPERTREND_MULTIPLIER
    
    # Risk management
    config_vars['MAX_CAPITAL_LOSS_PERCENT'] = config.MAX_CAPITAL_LOSS_PERCENT
    config_vars['DEFAULT_CAPITAL'] = config.DEFAULT_CAPITAL
    
    # Order management
    config_vars['RESPECT_EXISTING_ORDERS'] = config.RESPECT_EXISTING_ORDERS
    config_vars['AUTO_CANCEL_OLD_ORDERS'] = config.AUTO_CANCEL_OLD_ORDERS
    config_vars['MAX_ORDER_AGE_HOURS'] = config.MAX_ORDER_AGE_HOURS
    
    # Performance settings
    config_vars['MAX_ITERATION_TIME'] = config.MAX_ITERATION_TIME
    config_vars['PENDING_ORDER_MAX_ITERATIONS'] = config.PENDING_ORDER_MAX_ITERATIONS
    
    # Trading timing
    config_vars['ENABLE_CONTINUOUS_MONITORING'] = config.ENABLE_CONTINUOUS_MONITORING
    config_vars['ENABLE_CANDLE_CLOSE_ENTRIES'] = config.ENABLE_CANDLE_CLOSE_ENTRIES
    config_vars['MONITORING_INTERVAL'] = config.MONITORING_INTERVAL
    
    return config_vars

def update_config_file(changes):
    """Update config.py with new values"""
    # Create backup
    backup_file = create_backup()
    
    # Read current config file
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
    
    # Apply changes
    for var_name, new_value in changes.items():
        # Handle different data types
        if isinstance(new_value, bool):
            value_str = str(new_value)
        elif isinstance(new_value, str):
            value_str = f"'{new_value}'"
        else:
            value_str = str(new_value)
        
        # Replace the variable assignment
        import re
        pattern = rf'^{var_name}\s*=\s*.*$'
        replacement = f"{var_name} = {value_str}"
        
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write updated content
    with open(CONFIG_FILE, 'w') as f:
        f.write(content)
    
    return backup_file

@app.route('/')
def index():
    """Main configuration dashboard"""
    config_vars = get_config_variables()
    return render_template('config_dashboard.html', config_vars=config_vars)

@app.route('/api/config', methods=['GET'])
def get_config():
    """API endpoint to get current configuration"""
    config_vars = get_config_variables()
    return jsonify(config_vars)

@app.route('/api/config', methods=['POST'])
def update_config():
    """API endpoint to update configuration"""
    try:
        changes = request.json
        
        # Validate changes
        valid_vars = get_config_variables().keys()
        for var_name in changes.keys():
            if var_name not in valid_vars:
                return jsonify({'error': f'Invalid variable: {var_name}'}), 400
        
        # Update config file
        backup_file = update_config_file(changes)
        
        # Reload config module
        import importlib
        importlib.reload(config)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'backup_file': backup_file
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backups', methods=['GET'])
def list_backups():
    """List all configuration backups"""
    backups = []
    if os.path.exists(BACKUP_DIR):
        for file in os.listdir(BACKUP_DIR):
            if file.startswith('config_backup_') and file.endswith('.py'):
                file_path = os.path.join(BACKUP_DIR, file)
                stat = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'timestamp': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': stat.st_size
                })
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(backups)

@app.route('/api/backups/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore configuration from backup"""
    try:
        backup_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        # Create backup of current config before restoring
        current_backup = create_backup()
        
        # Restore from backup
        shutil.copy2(backup_path, CONFIG_FILE)
        
        # Reload config module
        import importlib
        importlib.reload(config)
        
        return jsonify({
            'success': True,
            'message': f'Configuration restored from {filename}',
            'current_backup': current_backup
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_config():
    """Validate configuration changes without applying them"""
    try:
        changes = request.json
        config_vars = get_config_variables()
        
        # Apply changes to a copy for validation
        test_config = config_vars.copy()
        test_config.update(changes)
        
        # Validation rules
        errors = []
        
        if 'LEVERAGE' in changes:
            if not (1 <= test_config['LEVERAGE'] <= 100):
                errors.append('LEVERAGE must be between 1 and 100')
        
        if 'POSITION_SIZE_PERCENT' in changes:
            if not (0.01 <= test_config['POSITION_SIZE_PERCENT'] <= 1.0):
                errors.append('POSITION_SIZE_PERCENT must be between 0.01 and 1.0')
        
        if 'TAKE_PROFIT_MULTIPLIER' in changes:
            if not (0.1 <= test_config['TAKE_PROFIT_MULTIPLIER'] <= 10.0):
                errors.append('TAKE_PROFIT_MULTIPLIER must be between 0.1 and 10.0')
        
        if 'SUPERTREND_PERIOD' in changes:
            if not (1 <= test_config['SUPERTREND_PERIOD'] <= 50):
                errors.append('SUPERTREND_PERIOD must be between 1 and 50')
        
        if 'SUPERTREND_MULTIPLIER' in changes:
            if not (0.1 <= test_config['SUPERTREND_MULTIPLIER'] <= 10.0):
                errors.append('SUPERTREND_MULTIPLIER must be between 0.1 and 10.0')
        
        if errors:
            return jsonify({'valid': False, 'errors': errors})
        else:
            return jsonify({'valid': True, 'message': 'Configuration is valid'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌐 Starting Web Configuration Server...")
    print("📱 Access the dashboard at: http://localhost:5000")
    print("🔧 API endpoints available at: http://localhost:5000/api/")
    app.run(host='0.0.0.0', port=5000, debug=True) 