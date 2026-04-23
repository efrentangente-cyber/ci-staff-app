"""
Check the structure of the users table in PostgreSQL
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    exit(1)

print(f"🔗 Connecting to PostgreSQL...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Get column information
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'users'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    
    print(f"\n📊 Users Table Structure:")
    print("=" * 80)
    print(f"{'Column Name':<30} {'Data Type':<20} {'Nullable':<10}")
    print("-" * 80)
    
    for col_name, data_type, is_nullable in columns:
        print(f"{col_name:<30} {data_type:<20} {is_nullable:<10}")
    
    print("=" * 80)
    
    # Check for required columns
    required_columns = [
        'id', 'email', 'password_hash', 'name', 'role', 'is_approved',
        'signature_path', 'backup_email', 'profile_photo', 'assigned_route', 'permissions'
    ]
    
    existing_columns = [col[0] for col in columns]
    
    print(f"\n🔍 Checking Required Columns:")
    print("=" * 80)
    
    missing_columns = []
    for col in required_columns:
        if col in existing_columns:
            print(f"✓ {col}")
        else:
            print(f"✗ {col} - MISSING!")
            missing_columns.append(col)
    
    if missing_columns:
        print(f"\n⚠️  Missing columns: {', '.join(missing_columns)}")
        print(f"\nThis might cause errors when loading users!")
    else:
        print(f"\n✅ All required columns exist!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
