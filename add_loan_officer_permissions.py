#!/usr/bin/env python3
"""
Add permissions column to users table for loan officer access control
"""

import sqlite3

def add_permissions_column():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'permissions' not in columns:
            print("Adding 'permissions' column to users table...")
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN permissions TEXT DEFAULT NULL
            ''')
            conn.commit()
            print("✓ Column added successfully")
            
            # Set default permissions for existing loan officers
            cursor.execute('''
                UPDATE users 
                SET permissions = 'manage_users,system_settings'
                WHERE role = 'loan_officer'
            ''')
            conn.commit()
            print("✓ Default permissions set for existing loan officers")
        else:
            print("✓ Column 'permissions' already exists")
        
        # Display current users with permissions
        print("\nCurrent users with permissions:")
        cursor.execute('''
            SELECT id, name, email, role, permissions 
            FROM users 
            WHERE role IN ('admin', 'loan_officer')
            ORDER BY role, name
        ''')
        
        for user in cursor.fetchall():
            print(f"  {user[1]:25} ({user[2]:30}) - Role: {user[3]:15} - Permissions: {user[4] or 'None'}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("ADDING LOAN OFFICER PERMISSIONS SYSTEM")
    print("=" * 70)
    add_permissions_column()
    print("\n" + "=" * 70)
    print("✅ COMPLETE")
    print("=" * 70)
