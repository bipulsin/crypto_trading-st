#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import json
import sqlite3
import signal
import psutil
from datetime import datetime
from typing import Dict, Optional, List
import logging

class StrategyManager:
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.processes = {}  # Store running processes by user_id and strategy
        self.setup_logging()
        self.init_db()
        
    def setup_logging(self):
        """Setup logging for strategy manager"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('strategy_manager.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_db(self):
        """Initialize database tables for strategy management"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create strategy_status table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    is_running BOOLEAN DEFAULT FALSE,
                    process_id INTEGER,
                    start_time TIMESTAMP,
                    stop_time TIMESTAMP,
                    pnl REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create strategy_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    log_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            self.logger.info("Database initialized for strategy management")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    def get_broker_connection(self, user_id: str, strategy_name: str) -> Optional[Dict]:
        """Get broker connection details for a strategy"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT bc.* FROM broker_connections bc
                JOIN strategy_configs sc ON bc.id = sc.broker_connection_id
                WHERE sc.user_id = ? AND sc.strategy_name = ? AND sc.is_active = 1
                ORDER BY sc.updated_at DESC LIMIT 1
            ''', (user_id, strategy_name))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'connection_name': row[2],
                    'broker_id': row[3],
                    'broker_url': row[4],
                    'api_key': row[5],
                    'api_secret': row[6],
                    'created_at': row[7]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get broker connection: {e}")
            return None

    def get_strategy_config(self, user_id: str, strategy_name: str) -> Optional[Dict]:
        """Get strategy configuration from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM strategy_configs 
                WHERE user_id = ? AND strategy_name = ? AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
            ''', (user_id, strategy_name))
            
            row = cursor.fetchone()
            if row:
                config_data = json.loads(row[5]) if row[5] else {}
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'strategy_name': row[2],
                    'broker_connection_id': row[3],
                    'is_active': row[4],
                    'config_data': config_data,
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get strategy config: {e}")
            return None
    
    def start_strategy(self, user_id: str, strategy_name: str) -> bool:
        """Start a strategy for a user"""
        try:
            # Check if strategy is already running
            if self.is_strategy_running(user_id, strategy_name):
                self.logger.warning(f"Strategy {strategy_name} is already running for user {user_id}")
                return False
            
            # Get broker connection and strategy config
            broker_conn = self.get_broker_connection(user_id, strategy_name)
            strategy_config = self.get_strategy_config(user_id, strategy_name)
            
            if not broker_conn:
                self.log_strategy_event(user_id, strategy_name, "ERROR", f"No broker connection found for strategy {strategy_name}")
                self.logger.error(f"No broker connection found for strategy {strategy_name}")
                return False
            
            if not strategy_config:
                self.log_strategy_event(user_id, strategy_name, "ERROR", f"No configuration found for strategy {strategy_name}")
                self.logger.error(f"No configuration found for strategy {strategy_name}")
                return False
            
            # Log strategy start attempt
            self.log_strategy_event(user_id, strategy_name, "INFO", f"Attempting to start {strategy_name} strategy")
            
            # Get the strategy script path
            script_path = os.path.join(os.path.dirname(__file__), f"{strategy_name}.py")
            if not os.path.exists(script_path):
                script_path = os.path.join(os.path.dirname(__file__), f"strategy_{strategy_name}.py")
            
            if not os.path.exists(script_path):
                self.log_strategy_event(user_id, strategy_name, "ERROR", f"Strategy script not found: {script_path}")
                self.logger.error(f"Strategy script not found: {script_path}")
                return False
            
            # Prepare environment variables for the strategy
            env = os.environ.copy()
            env.update({
                'USER_ID': user_id,
                'STRATEGY_NAME': strategy_name,
                'BASE_URL': broker_conn['broker_url'],
                'API_KEY': broker_conn['api_key'],
                'API_SECRET': broker_conn['api_secret'],
                'BROKER_CONNECTION_ID': str(broker_conn['id']),
                'CONNECTION_NAME': broker_conn['connection_name']
            })
            
            # Add strategy-specific config as environment variables
            for key, value in strategy_config['config_data'].items():
                env[f'STRATEGY_{key.upper()}'] = str(value)
            
            # Start the strategy process
            process = subprocess.Popen(
                [sys.executable, script_path, '--user-id', user_id, '--strategy-name', strategy_name],
                env=env,
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait a moment for the process to start and check for immediate errors
            time.sleep(3)
            if process.poll() is not None:
                # Process exited immediately, get the error
                stdout, stderr = process.communicate()
                error_msg = f"Strategy process exited immediately. stdout: {stdout}, stderr: {stderr}"
                self.log_strategy_event(user_id, strategy_name, "ERROR", error_msg)
                self.logger.error(error_msg)
                return False
            
            # Check if process is still running after a bit more time
            time.sleep(2)
            if process.poll() is not None:
                # Process exited after initial startup, get the error
                stdout, stderr = process.communicate()
                error_msg = f"Strategy process exited after startup. stdout: {stdout}, stderr: {stderr}"
                self.log_strategy_event(user_id, strategy_name, "ERROR", error_msg)
                self.logger.error(error_msg)
                return False
            
            # Store the process in our processes dictionary
            key = f"{user_id}_{strategy_name}"
            self.processes[key] = process
            
            # Update strategy status
            self.update_strategy_status(user_id, strategy_name, True, process.pid)
            self.log_strategy_event(user_id, strategy_name, "INFO", f"Strategy {strategy_name} started successfully with PID {process.pid}")
            
            self.logger.info(f"Started strategy {strategy_name} for user {user_id} with PID {process.pid}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to start strategy {strategy_name} for user {user_id}: {str(e)}"
            self.log_strategy_event(user_id, strategy_name, "ERROR", error_msg)
            self.logger.error(error_msg)
            return False
    
    def stop_strategy(self, user_id: str, strategy_name: str) -> bool:
        """Stop a strategy for a user"""
        try:
            key = f"{user_id}_{strategy_name}"
            
            # Log strategy stop attempt
            self.log_strategy_event(user_id, strategy_name, "INFO", f"Attempting to stop {strategy_name} strategy")
            
            # Check if process is running
            if key in self.processes:
                process = self.processes[key]
                
                # Try to terminate gracefully
                process.terminate()
                self.log_strategy_event(user_id, strategy_name, "INFO", f"Sent termination signal to process {process.pid}")
                
                # Wait for process to terminate (5 seconds)
                try:
                    process.wait(timeout=5)
                    self.log_strategy_event(user_id, strategy_name, "INFO", f"Process {process.pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    process.kill()
                    process.wait()
                    self.log_strategy_event(user_id, strategy_name, "WARNING", f"Process {process.pid} was force-killed after timeout")
                
                del self.processes[key]
                self.logger.info(f"Stopped strategy {strategy_name} for user {user_id}")
            else:
                self.log_strategy_event(user_id, strategy_name, "INFO", "No running process found for strategy")
            
            # Also check for any orphaned processes
            self.kill_orphaned_processes(user_id, strategy_name)
            
            # Update database
            self.update_strategy_status(user_id, strategy_name, False)
            self.log_strategy_event(user_id, strategy_name, "INFO", f"Strategy {strategy_name} stopped successfully")
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to stop strategy {strategy_name} for user {user_id}: {str(e)}"
            self.log_strategy_event(user_id, strategy_name, "ERROR", error_msg)
            self.logger.error(error_msg)
            return False
    
    def kill_orphaned_processes(self, user_id: str, strategy_name: str):
        """Kill any orphaned processes for the strategy"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 2:
                        if (strategy_name in ' '.join(cmdline) and 
                            any(user_id in arg for arg in cmdline if arg)):
                            self.logger.info(f"Killing orphaned process {proc.info['pid']}")
                            psutil.Process(proc.info['pid']).terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.error(f"Error killing orphaned processes: {str(e)}")
    
    def is_strategy_running(self, user_id: str, strategy_name: str) -> bool:
        """Check if a strategy is running for a user"""
        # Check local processes first
        key = f"{user_id}_{strategy_name}"
        if key in self.processes:
            process = self.processes[key]
            if process.poll() is None:  # Process is still running
                return True
            else:
                # Process has ended, clean up
                del self.processes[key]
        
        # Check database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_running FROM strategy_status 
                WHERE user_id = ? AND strategy_name = ? 
                ORDER BY last_updated DESC LIMIT 1
            ''', (user_id, strategy_name))
            
            result = cursor.fetchone()
            conn.close()
            
            return bool(result[0]) if result else False
        except Exception as e:
            self.logger.error(f"Failed to check strategy status: {e}")
            return False
    
    def update_strategy_status(self, user_id: str, strategy_name: str, is_running: bool, process_id: int = None):
        """Update strategy status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if is_running:
                cursor.execute('''
                    INSERT OR REPLACE INTO strategy_status 
                    (user_id, strategy_name, is_running, process_id, start_time, last_updated)
                    VALUES (?, ?, TRUE, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, strategy_name, process_id))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO strategy_status 
                    (user_id, strategy_name, is_running, stop_time, last_updated)
                    VALUES (?, ?, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, strategy_name))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to update strategy status: {e}")
    
    def log_strategy_event(self, user_id: str, strategy_name: str, level: str, message: str):
        """Log strategy events to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO strategy_logs (user_id, strategy_name, log_level, message)
                VALUES (?, ?, ?, ?)
            ''', (user_id, strategy_name, level, message))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to log strategy event: {e}")
    
    def get_strategy_logs(self, user_id: str, strategy_name: str, limit: int = 50) -> List[Dict]:
        """Get strategy logs from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT log_level, message, timestamp
                FROM strategy_logs 
                WHERE user_id = ? AND strategy_name = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, strategy_name, limit))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'level': row[0],
                    'message': row[1],
                    'timestamp': row[2]
                })
            
            conn.close()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to get strategy logs: {e}")
            return []
    
    def get_strategy_status(self, user_id: str, strategy_name: str) -> Dict:
        """Get current strategy status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT is_running, start_time, stop_time, pnl, last_updated, process_id
                FROM strategy_status 
                WHERE user_id = ? AND strategy_name = ?
                ORDER BY last_updated DESC LIMIT 1
            ''', (user_id, strategy_name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'is_running': bool(result[0]),
                    'start_time': result[1],
                    'stop_time': result[2],
                    'pnl': float(result[3]),
                    'last_updated': result[4],
                    'process_id': result[5]
                }
            else:
                return {
                    'is_running': False,
                    'start_time': None,
                    'stop_time': None,
                    'pnl': 0.0,
                    'last_updated': datetime.now().isoformat(),
                    'process_id': None,
                    'error': str(e)
                }
        except Exception as e:
            self.logger.error(f"Failed to get strategy status: {e}")
            return {
                'is_running': False,
                'start_time': None,
                'stop_time': None,
                'pnl': 0.0,
                'last_updated': datetime.now().isoformat(),
                'process_id': None,
                'error': str(e)
            }

    def save_strategy_config(self, user_id: str, strategy_name: str, broker_connection_id: Optional[int], config_data: Dict) -> bool:
        """Save strategy configuration to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First, deactivate any existing active configs for this user and strategy
            cursor.execute('''
                UPDATE strategy_configs 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND strategy_name = ?
            ''', (user_id, strategy_name))
            
            # Insert new configuration
            cursor.execute('''
                INSERT INTO strategy_configs (
                    user_id, strategy_name, broker_connection_id, 
                    symbol, symbol_id, config_data, is_active, 
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                user_id, strategy_name, broker_connection_id,
                'BTCUSD', 84, json.dumps(config_data), True
            ))
            
            conn.commit()
            conn.close()
            
            self.log_strategy_event(user_id, strategy_name, "INFO", f"Configuration saved for {strategy_name} strategy")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save strategy config: {e}")
            return False

# Global strategy manager instance
strategy_manager = StrategyManager()
