"""
Setup default users in PostgreSQL database on Render
Run this script to create/update login accounts
"""

import os
from dotenv import load_dotenv
from database import get_db
from werkzeug.security import generate_password_hash

load_dotenv()

def setup_users():
    """Create or update default users in PostgreSQL"""
    try:
        conn = get_db()
        
        # Default users with their credentials
        users = [
            {
                'email': 'admin@dccco.test',
                'password': 'admin123',
                'name': 'Super Admin',
                'role': 'admin'
            },
            {
                'email': 'loan@dccco.test',
                'password': 'loan123',
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
                'email': 'lps@dccco.test',
                'password': 'lps123',
                'name': 'LPS Staff',
                'role': 'loan_staff'
            }
        ]
        
        print("\n🔧 Setting up users in PostgreSQL...")
        print("=" * 60)
        
        for user_data in users:
            email = user_data['email']
            password = user_data['password']
            name = user_data['name']
            role = user_data['role']
            
            # Check if user exists
            existing = conn.execute('SELECT id, role FROM users WHERE email = %s', (email,)).fetchone()
            
            if existing:
                # Update existing user
                password_hash = generate_password_hash(password)
                conn.execute('''
                    UPDATE users 
                    SET password_hash = %s, name = %s, role = %s, is_approved = 1
                    WHERE email = %s
                ''', (password_hash, name, role, email))
                print(f"✓ Updated: {email} ({role})")
            else:
                # Create new user
                password_hash = generate_password_hash(password)
                conn.execute('''
                    INSERT INTO users (email, password_hash, name, role, is_approved)
                    VALUES (%s, %s, %s, %s, 1)
                ''', (email, password_hash, name, role))
                print(f"✓ Created: {email} ({role})")
        
        conn.commit()
        print("=" * 60)
        print("✅ All users setup complete!\n")
        
        # Display login credentials
        print("📋 LOGIN CREDENTIALS:")
        print("=" * 60)
        for user_data in users:
            print(f"Role: {user_data['role'].upper()}")
            print(f"  Email: {user_data['email']}")
            print(f"  Password: {user_data['password']}")
            print()
        
        # Verify users were created
        print("🔍 Verifying users in database...")
        all_users = conn.execute('SELECT id, email, name, role, is_approved FROM users ORDER BY role').fetchall()
        print(f"Total users in database: {len(all_users)}")
        for user in all_users:
            status = "✓ Approved" if user['is_approved'] else "✗ Pending"
            print(f"  - {user['email']} ({user['role']}) {status}")
        
        conn.close()
        print("\n✅ Setup complete! You can now login to Render.")
        
    except Exception as e:
        print(f"\n❌ Error setting up users: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    setup_users()
