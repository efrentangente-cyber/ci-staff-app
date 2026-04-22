#!/usr/bin/env python3
"""
Reset all user passwords to simple testing passwords for local development
WARNING: Only use this for local testing, never in production!
"""

import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'app.db'

def reset_passwords():
    """Reset all user passwords to simple testing passwords"""
    
    # Define test passwords for each role
    test_users = [
        ('superadmin@dccco.test', 'admin123', 'Super Admin', 'admin'),
        ('admin@dccco.test', 'admin123', 'Loan Officer', 'loan_officer'),
        ('loan@dccco.test', 'loan123', 'Loan Staff', 'loan_staff'),
        ('ci@dccco.test', 'ci123', 'CI Staff', 'ci_staff'),
    ]
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("RESETTING TEST PASSWORDS")
        print("=" * 60)
        print()
        
        for email, password, name, role in test_users:
            # Check if user exists
            cursor.execute('SELECT id, name, role FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if user:
                # Update existing user
                password_hash = generate_password_hash(password)
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, name = ?, role = ?, is_approved = 1
                    WHERE email = ?
                ''', (password_hash, name, role, email))
                print(f"✓ Updated: {email}")
                print(f"  Name: {name}")
                print(f"  Role: {role}")
                print(f"  Password: {password}")
                print()
            else:
                # Create new user
                password_hash = generate_password_hash(password)
                cursor.execute('''
                    INSERT INTO users (email, password_hash, name, role, is_approved)
                    VALUES (?, ?, ?, ?, 1)
                ''', (email, password_hash, name, role))
                print(f"✓ Created: {email}")
                print(f"  Name: {name}")
                print(f"  Role: {role}")
                print(f"  Password: {password}")
                print()
        
        conn.commit()
        
        # Show all users
        print("=" * 60)
        print("ALL USERS IN DATABASE")
        print("=" * 60)
        cursor.execute('SELECT id, email, name, role, is_approved FROM users ORDER BY role, email')
        users = cursor.fetchall()
        
        for user in users:
            user_id, email, name, role, is_approved = user
            status = "✓ Approved" if is_approved else "✗ Pending"
            print(f"ID: {user_id:2d} | {email:30s} | {name:20s} | {role:15s} | {status}")
        
        print()
        print("=" * 60)
        print("TEST CREDENTIALS")
        print("=" * 60)
        print()
        print("Super Admin:")
        print("  Email: superadmin@dccco.test")
        print("  Password: admin123")
        print()
        print("Loan Officer:")
        print("  Email: admin@dccco.test")
        print("  Password: admin123")
        print()
        print("Loan Staff (LPS):")
        print("  Email: loan@dccco.test")
        print("  Password: loan123")
        print()
        print("CI Staff:")
        print("  Email: ci@dccco.test")
        print("  Password: ci123")
        print()
        print("=" * 60)
        print("✓ Password reset completed successfully!")
        print("=" * 60)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    reset_passwords()
