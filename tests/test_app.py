#!/usr/bin/env python3

"""
Automated tests for Trade Manthan Web Application
This script runs comprehensive tests on the application before deployment
"""

import unittest
import sys
import os
import sqlite3
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestTradeManthanApp(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_path = 'test_users.db'
        
        # Create test database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create test tables
        self.create_test_tables()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def create_test_tables(self):
        """Create test database tables"""
        # Users table
        self.cursor.execute('''
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
        
        # Strategy status table
        self.cursor.execute('''
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
        
        # Strategy logs table
        self.cursor.execute('''
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
    
    def test_database_connection(self):
        """Test database connection and table creation"""
        self.assertIsNotNone(self.conn)
        self.assertIsNotNone(self.cursor)
        
        # Check if tables exist
        tables = ['users', 'strategy_status', 'strategy_logs']
        for table in tables:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            result = self.cursor.fetchone()
            self.assertIsNotNone(result, f"Table {table} should exist")
    
    def test_strategy_status_operations(self):
        """Test strategy status operations"""
        user_id = "TM12345"
        strategy_name = "supertrend"
        
        # Test inserting strategy status
        self.cursor.execute('''
            INSERT INTO strategy_status (user_id, strategy_name, is_running, start_time)
            VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
        ''', (user_id, strategy_name))
        self.conn.commit()
        
        # Test reading strategy status
        self.cursor.execute('''
            SELECT is_running FROM strategy_status 
            WHERE user_id = ? AND strategy_name = ?
        ''', (user_id, strategy_name))
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertTrue(result[0])
    
    def test_strategy_logs_operations(self):
        """Test strategy logs operations"""
        user_id = "TM12345"
        strategy_name = "supertrend"
        
        # Test inserting log entry
        self.cursor.execute('''
            INSERT INTO strategy_logs (user_id, strategy_name, log_level, message)
            VALUES (?, ?, 'INFO', 'Test log message')
        ''', (user_id, strategy_name))
        self.conn.commit()
        
        # Test reading log entries
        self.cursor.execute('''
            SELECT message FROM strategy_logs 
            WHERE user_id = ? AND strategy_name = ?
        ''', (user_id, strategy_name))
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'Test log message')

class TestImports(unittest.TestCase):
    """Test that all required modules can be imported"""
    
    def test_app_import(self):
        """Test app module import"""
        try:
            import app
            self.assertTrue(True, "App module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import app module: {e}")
    
    def test_strategy_manager_import(self):
        """Test strategy_manager module import"""
        try:
            import strategy_manager
            self.assertTrue(True, "Strategy manager module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import strategy_manager module: {e}")
    
    def test_strategy_st_import(self):
        """Test strategy_st module import"""
        try:
            import strategy_st
            self.assertTrue(True, "Strategy ST module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import strategy_st module: {e}")

class TestConfiguration(unittest.TestCase):
    """Test configuration and environment setup"""
    
    def test_required_files_exist(self):
        """Test that required files exist"""
        required_files = [
            'app.py',
            'strategy_manager.py',
            'strategy_st.py',
            'requirements.txt',
            'config.py',
            'delta_api.py',
            'supertrend.py'
        ]
        
        for file in required_files:
            self.assertTrue(os.path.exists(file), f"Required file {file} should exist")
    
    def test_requirements_file(self):
        """Test requirements.txt file"""
        self.assertTrue(os.path.exists('requirements.txt'))
        
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        # Check for essential dependencies
        essential_deps = ['flask', 'flask-login', 'google-auth', 'psutil']
        for dep in essential_deps:
            self.assertIn(dep, requirements, f"Essential dependency {dep} should be in requirements.txt")

def run_tests():
    """Run all tests"""
    print("🧪 Running Trade Manthan Application Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.makeSuite(TestTradeManthanApp))
    test_suite.addTest(unittest.makeSuite(TestImports))
    test_suite.addTest(unittest.makeSuite(TestConfiguration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
