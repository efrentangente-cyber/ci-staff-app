"""
Diagnostic script to check Render environment
This will print helpful debug info in Render logs
"""

import os
import sys

print("\n" + "="*80)
print("🔍 RENDER DIAGNOSTIC REPORT")
print("="*80)

# Check Python version
print(f"\n📌 Python Version: {sys.version}")

# Check if running on Render
print(f"\n📌 Environment:")
print(f"   RENDER: {os.getenv('RENDER', 'Not set')}")
print(f"   RENDER_SERVICE_NAME: {os.getenv('RENDER_SERVICE_NAME', 'Not set')}")

# Check DATABASE_URL
database_url = os.getenv('DATABASE_URL')
print(f"\n📌 Database Configuration:")
if database_url:
    # Hide password for security
    if '@' in database_url:
        parts = database_url.split('@')
        safe_url = parts[0].split(':')[0] + ':***@' + parts[1]
    else:
        safe_url = database_url[:20] + '...'
    print(f"   DATABASE_URL: {safe_url}")
    
    if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
        print(f"   ✓ PostgreSQL URL detected")
    elif database_url.startswith('sqlite'):
        print(f"   ⚠️  SQLite URL detected (should be PostgreSQL on Render!)")
    else:
        print(f"   ❌ Unknown database type")
else:
    print(f"   ❌ DATABASE_URL is NOT SET!")
    print(f"   This is why the app can't connect to the database.")
    print(f"   You MUST set DATABASE_URL in Render dashboard.")

# Check other environment variables
print(f"\n📌 Other Environment Variables:")
env_vars = [
    'SECRET_KEY',
    'FLASK_ENV',
    'FLASK_DEBUG',
    'RESEND_API_KEY',
    'SEMAPHORE_API_KEY'
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Show first 10 chars only for security
        safe_value = value[:10] + '...' if len(value) > 10 else value
        print(f"   ✓ {var}: {safe_value}")
    else:
        print(f"   ✗ {var}: Not set")

# Check if psycopg2 is installed
print(f"\n📌 PostgreSQL Driver:")
try:
    import psycopg2
    print(f"   ✓ psycopg2 installed (version: {psycopg2.__version__})")
except ImportError:
    print(f"   ❌ psycopg2 NOT installed!")
    print(f"   Run: pip install psycopg2-binary")

# Check if we can connect to database
print(f"\n📌 Database Connection Test:")
try:
    from database import get_db, get_database_type
    db_type = get_database_type()
    print(f"   Database type: {db_type.upper()}")
    
    if db_type == 'postgresql':
        print(f"   Attempting PostgreSQL connection...")
        conn = get_db()
        cursor = conn.execute("SELECT 1 as test")
        result = cursor.fetchone()
        conn.close()
        print(f"   ✓ PostgreSQL connection successful!")
    else:
        print(f"   ⚠️  Using SQLite (should be PostgreSQL on Render)")
        
except Exception as e:
    print(f"   ❌ Connection failed: {e}")

print("\n" + "="*80)
print("🔍 END OF DIAGNOSTIC REPORT")
print("="*80 + "\n")

# If DATABASE_URL is not set, provide instructions
if not database_url:
    print("\n" + "!"*80)
    print("⚠️  CRITICAL: DATABASE_URL is not set!")
    print("!"*80)
    print("\nTO FIX THIS:")
    print("1. Go to https://dashboard.render.com")
    print("2. Click on your web service")
    print("3. Click 'Environment' in the left sidebar")
    print("4. Click 'Add Environment Variable'")
    print("5. Add:")
    print("   Key: DATABASE_URL")
    print("   Value: postgresql://dccco_app:***@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj")
    print("6. Click 'Save Changes'")
    print("7. Wait for automatic redeploy (2-3 minutes)")
    print("\n" + "!"*80 + "\n")
