#!/usr/bin/env python3
"""
Verify login credentials and check password hashes
"""

import sqlite3
from werkzeug.security import check_password_hash

DATABASE = 'app.db'

def verify_login():
    """Test login credentials"""
    
    test_credentials = [
        ('superadmin@dccco.test', 'admin123'),
        ('admin@dccco.test', 'admin123'),
        ('loan@dccco.test', 'loan123'),
        ('ci@dccco.test', 'ci123'),
    ]
    
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("=" * 70)
        print("VERIFYING LOGIN CREDENTIALS")
        print("=" * 70)
        print()
        
        for email, password in test_credentials:
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if user:
                password_valid = check_password_hash(user['password_hash'], password)
                status = "✓ VALID" if password_valid else "✗ INVALID"
                
                print(f"Email: {email}")
                print(f"  Password: {password}")
                print(f"  Status: {status}")
                print(f"  Name: {user['name']}")
                print(f"  Role: {user['role']}")
                print(f"  Approved: {'Yes' if user['is_approved'] else 'No'}")
                print(f"  Hash (first 50 chars): {user['password_hash'][:50]}...")
                print()
            else:
                print(f"Email: {email}")
                print(f"  Status: ✗ USER NOT FOUND")
                print()
        
        print("=" * 70)
        print("ALL USERS IN DATABASE")
        print("=" * 70)
        cursor.execute('SELECT id, email, name, role, is_approved FROM users')
        users = cursor.fetchall()
        
        for user in users:
            approved = "✓" if user['is_approved'] else "✗"
            print(f"[{approved}] ID:{user['id']:2d} | {user['email']:35s} | {user['name']:20s} | {user['role']}")
        
        print()
        print("=" * 70)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_login()
