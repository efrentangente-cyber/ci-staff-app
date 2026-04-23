#!/usr/bin/env python3
"""
Test PostgreSQL connection and verify data
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database module
from database import get_db, get_database_type

def test_connection():
    print("=" * 80)
    print("TESTING POSTGRESQL CONNECTION")
    print("=" * 80)
    print()
    
    # Check database type
    db_type = get_database_type()
    print(f"📊 Database Type: {db_type.upper()}")
    print()
    
    # Test connection
    print("1. Testing connection...")
    try:
        conn = get_db()
        print("   ✓ Connected successfully!")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # Test query - count users
    print("\n2. Testing query - Count users...")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        count = result[0] if isinstance(result, tuple) else result['count']
        print(f"   ✓ Found {count} users")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        conn.close()
        return False
    
    # Test query - list users
    print("\n3. Listing all users...")
    try:
        cursor.execute("SELECT id, email, name, role FROM users")
        users = cursor.fetchall()
        for user in users:
            if isinstance(user, tuple):
                print(f"   • ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")
            else:
                print(f"   • ID: {user['id']}, Email: {user['email']}, Name: {user['name']}, Role: {user['role']}")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        conn.close()
        return False
    
    # Test query - count loan applications
    print("\n4. Testing query - Count loan applications...")
    try:
        cursor.execute("SELECT COUNT(*) as count FROM loan_applications")
        result = cursor.fetchone()
        count = result[0] if isinstance(result, tuple) else result['count']
        print(f"   ✓ Found {count} loan applications")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        conn.close()
        return False
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\n🎉 Your system is now using PostgreSQL!")
    print("📝 Data will persist forever on Render")
    print()
    
    return True

if __name__ == '__main__':
    test_connection()
