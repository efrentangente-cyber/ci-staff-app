#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Presentation Ready Script
Final checks and optimizations before presentation
"""

import os
import sqlite3
import sys

def check_database():
    """Check database integrity and permissions"""
    print("\n[OK] Checking database...")
    
    if not os.path.exists('app.db'):
        print("  [ERROR] app.db not found!")
        return False
    
    # Check if database is writable
    if not os.access('app.db', os.W_OK):
        print("  [WARNING] app.db is not writable!")
        print("    Fix: Run 'attrib -r app.db' on Windows")
        return False
    
    # Check database tables
    try:
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        required_tables = [
            'users', 'loan_applications', 'documents', 
            'ci_checklists', 'messages', 'notifications'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            print(f"  [WARNING] Missing tables: {', '.join(missing_tables)}")
        else:
            print(f"  [OK] All required tables exist")
        
        # Check for users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"  [OK] Users in database: {user_count}")
        
        # Check for applications
        cursor.execute("SELECT COUNT(*) FROM loan_applications")
        app_count = cursor.fetchone()[0]
        print(f"  [OK] Loan applications: {app_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Database error: {e}")
        return False

def check_critical_files():
    """Check if all critical files exist"""
    print("\n[OK] Checking critical files...")
    
    critical_files = {
        'app.py': 'Main application',
        'app.db': 'Database',
        'requirements.txt': 'Dependencies',
        'schema.sql': 'Database schema',
        '.env': 'Environment variables',
    }
    
    all_good = True
    for filename, description in critical_files.items():
        if os.path.exists(filename):
            print(f"  [OK] {filename} ({description})")
        else:
            print(f"  [MISSING] {filename} ({description})")
            all_good = False
    
    return all_good

def check_directories():
    """Check if required directories exist"""
    print("\n[OK] Checking directories...")
    
    required_dirs = [
        'static', 'templates', 'uploads', 'signatures',
        'message_attachments', 'voice_messages'
    ]
    
    for dirname in required_dirs:
        if os.path.exists(dirname):
            print(f"  [OK] {dirname}/")
        else:
            print(f"  [CREATING] {dirname}/")
            os.makedirs(dirname, exist_ok=True)
    
    return True

def check_env_variables():
    """Check environment variables"""
    print("\n[OK] Checking environment variables...")
    
    if not os.path.exists('.env'):
        print("  [WARNING] .env file not found")
        return False
    
    with open('.env', 'r') as f:
        env_content = f.read()
    
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    optional_vars = ['SEMAPHORE_API_KEY', 'OPENAI_API_KEY']
    
    for var in required_vars:
        if var in env_content:
            print(f"  [OK] {var} is set")
        else:
            print(f"  [WARNING] {var} not found in .env")
    
    for var in optional_vars:
        if var in env_content:
            print(f"  [OK] {var} is set (optional)")
    
    return True

def main():
    """Run all checks"""
    print("=" * 60)
    print("PRESENTATION READINESS CHECK")
    print("=" * 60)
    
    checks = [
        check_critical_files(),
        check_directories(),
        check_database(),
        check_env_variables(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("[SUCCESS] ALL CHECKS PASSED - SYSTEM READY FOR PRESENTATION!")
    else:
        print("[WARNING] SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
        print("\nQuick fixes:")
        print("  1. Database not writable: attrib -r app.db")
        print("  2. Missing .env: Copy from .env.example")
        print("  3. Missing tables: python schema.sql")
    print("=" * 60)
    
    return all(checks)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
