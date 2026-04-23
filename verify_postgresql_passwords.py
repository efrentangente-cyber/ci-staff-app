"""
Verify and reset passwords for default users in PostgreSQL
"""

import os
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

print(f"🔗 Connecting to PostgreSQL...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Default credentials
    default_users = [
        ('admin@dccco.test', 'admin123', 'Super Admin', 'admin'),
        ('loan@dccco.test', 'loan123', 'Loan Officer', 'loan_officer'),
        ('ci@dccco.test', 'ci123', 'CI Staff', 'ci_staff'),
        ('lps@dccco.test', 'lps123', 'LPS Staff', 'loan_staff')
    ]
    
    print("\n🔐 Resetting passwords for default users...")
    print("=" * 80)
    
    for email, password, name, role in default_users:
        # Check if user exists
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            user_id, old_hash = user
            
            # Generate new password hash
            new_hash = generate_password_hash(password)
            
            # Update password and ensure user is approved
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s, name = %s, role = %s, is_approved = 1
                WHERE email = %s
            """, (new_hash, name, role, email))
            
            print(f"✓ Reset password: {email}")
            print(f"  Role: {role}")
            print(f"  Password: {password}")
            print()
        else:
            # Create new user
            new_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, is_approved)
                VALUES (%s, %s, %s, %s, 1)
            """, (email, new_hash, name, role))
            print(f"✓ Created new user: {email}")
            print(f"  Role: {role}")
            print(f"  Password: {password}")
            print()
    
    conn.commit()
    print("=" * 80)
    print("✅ All passwords reset successfully!\n")
    
    # Display login credentials
    print("📋 LOGIN CREDENTIALS FOR RENDER:")
    print("=" * 80)
    for email, password, name, role in default_users:
        print(f"{role.upper()}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print()
    
    print("=" * 80)
    print("✅ You can now login to your Render deployment!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
