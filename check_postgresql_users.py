"""
Check what users exist in PostgreSQL database on Render
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Force PostgreSQL connection
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

print(f"🔗 Connecting to PostgreSQL...")
print(f"   URL: {DATABASE_URL[:50]}...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if users table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        )
    """)
    table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        print("❌ Users table does not exist in PostgreSQL!")
        print("   You need to run the migration script first.")
        conn.close()
        exit(1)
    
    print("✓ Users table exists")
    
    # Get all users
    cursor.execute("""
        SELECT id, email, name, role, is_approved, created_at
        FROM users
        ORDER BY role, email
    """)
    users = cursor.fetchall()
    
    print(f"\n📊 Total users in PostgreSQL: {len(users)}")
    print("=" * 80)
    
    if len(users) == 0:
        print("⚠️  NO USERS FOUND! This is why you can't login.")
        print("   Need to create default users.")
    else:
        print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Role':<15} {'Approved':<10}")
        print("-" * 80)
        for user in users:
            user_id, email, name, role, is_approved, created_at = user
            approved_status = "✓ Yes" if is_approved else "✗ No"
            print(f"{user_id:<5} {email:<30} {name:<20} {role:<15} {approved_status:<10}")
    
    print("=" * 80)
    
    # Check for default admin account
    cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@dccco.test',))
    admin_exists = cursor.fetchone()
    
    if admin_exists:
        print("✓ Default admin account exists: admin@dccco.test")
    else:
        print("❌ Default admin account NOT FOUND: admin@dccco.test")
        print("   This is why you can't login!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
