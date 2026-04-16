#!/usr/bin/env python3
"""
Production setup script - Run this once on Render to set up all users
"""
import sqlite3
from werkzeug.security import generate_password_hash

def setup_production():
    print("Setting up production database...")
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Check if super admin exists
    existing = cursor.execute('SELECT id FROM users WHERE email = ?', ('superadmin@dccco.test',)).fetchone()
    
    if existing:
        print("✓ Super admin already exists, skipping setup")
        conn.close()
        return
    
    print("Creating production users...")
    
    users = [
        {
            'email': 'superadmin@dccco.test',
            'password': 'admin@2024',
            'name': 'Super Admin',
            'role': 'admin'
        },
        {
            'email': 'admin@dccco.test',
            'password': 'admin123',
            'name': 'Loan Officer',
            'role': 'loan_officer'
        },
        {
            'email': 'ci@dccco.test',
            'password': 'ci123',
            'name': 'CI Staff',
            'role': 'ci_staff'
        },
        {
            'email': 'loan@dccco.test',
            'password': 'loan123',
            'name': 'Loan Staff',
            'role': 'loan_staff'
        }
    ]
    
    for user_data in users:
        # Check if exists
        existing = cursor.execute('SELECT id FROM users WHERE email = ?', (user_data['email'],)).fetchone()
        
        if not existing:
            password_hash = generate_password_hash(user_data['password'])
            cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, is_approved)
                VALUES (?, ?, ?, ?, 1)
            ''', (user_data['email'], password_hash, user_data['name'], user_data['role']))
            print(f"✓ Created {user_data['name']} ({user_data['email']})")
        else:
            # Update role and name
            cursor.execute('UPDATE users SET name = ?, role = ? WHERE email = ?',
                         (user_data['name'], user_data['role'], user_data['email']))
            print(f"✓ Updated {user_data['name']} ({user_data['email']})")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Production setup complete!")
    print("\nLogin credentials:")
    print("  Super Admin: superadmin@dccco.test / admin@2024")
    print("  Loan Officer: admin@dccco.test / admin123")
    print("  CI Staff: ci@dccco.test / ci123")
    print("  Loan Staff: loan@dccco.test / loan123")

if __name__ == '__main__':
    setup_production()
