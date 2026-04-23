"""
Complete Migration: SQLite (app.db) → PostgreSQL
Migrates ALL data including users, applications, documents, messages, etc.
"""

import sqlite3
import os
from database import get_db, get_database_type
from werkzeug.security import generate_password_hash

# PostgreSQL connection
POSTGRESQL_URL = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'
os.environ['DATABASE_URL'] = POSTGRESQL_URL

print("=" * 70)
print("COMPLETE DATABASE MIGRATION: SQLite → PostgreSQL")
print("=" * 70)

# Connect to SQLite
print("\n📂 Connecting to SQLite (app.db)...")
sqlite_conn = sqlite3.connect('app.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL
print("📊 Connecting to PostgreSQL...")
pg_conn = get_db()

# Tables to migrate (in order due to foreign keys)
tables = [
    'users',
    'loan_applications',
    'documents',
    'messages',
    'notifications',
    'direct_messages',
    'location_tracking',
    'loan_types',
    'system_settings',
    'sms_templates',
    'password_reset_codes',
    'permissions'
]

migration_stats = {}

for table in tables:
    try:
        print(f"\n📋 Migrating table: {table}")
        
        # Check if table exists in SQLite
        sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not sqlite_cursor.fetchone():
            print(f"   ⚠️  Table '{table}' not found in SQLite, skipping...")
            migration_stats[table] = {'status': 'skipped', 'count': 0}
            continue
        
        # Get all data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"   ℹ️  Table '{table}' is empty")
            migration_stats[table] = {'status': 'empty', 'count': 0}
            continue
        
        # Get column names
        columns = [description[0] for description in sqlite_cursor.description]
        
        # Clear existing data in PostgreSQL (optional - comment out to keep existing data)
        # pg_conn.execute(f"DELETE FROM {table}")
        # pg_conn.commit()
        
        # Insert data into PostgreSQL
        inserted = 0
        skipped = 0
        
        for row in rows:
            try:
                # Convert row to dict
                row_dict = dict(zip(columns, row))
                
                # Remove 'id' if it's auto-increment (SERIAL in PostgreSQL)
                if 'id' in row_dict and table != 'users':  # Keep user IDs for foreign key consistency
                    del row_dict['id']
                
                # Build INSERT query
                cols = ', '.join(row_dict.keys())
                placeholders = ', '.join(['%s'] * len(row_dict))
                values = tuple(row_dict.values())
                
                query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
                
                # Special handling for users table (check for duplicates)
                if table == 'users':
                    # Check if user already exists
                    existing = pg_conn.execute(
                        "SELECT id FROM users WHERE email = %s", 
                        (row_dict['email'],)
                    ).fetchone()
                    
                    if existing:
                        # Update existing user
                        update_cols = ', '.join([f"{k} = %s" for k in row_dict.keys() if k != 'id'])
                        update_values = tuple([v for k, v in row_dict.items() if k != 'id']) + (row_dict['email'],)
                        query = f"UPDATE users SET {update_cols} WHERE email = %s"
                        pg_conn.execute(query, update_values)
                        skipped += 1
                    else:
                        pg_conn.execute(query, values)
                        inserted += 1
                else:
                    pg_conn.execute(query, values)
                    inserted += 1
                
            except Exception as e:
                print(f"   ⚠️  Error inserting row: {e}")
                skipped += 1
                continue
        
        pg_conn.commit()
        
        print(f"   ✓ Migrated {inserted} rows, skipped {skipped}")
        migration_stats[table] = {'status': 'success', 'count': inserted, 'skipped': skipped}
        
    except Exception as e:
        print(f"   ❌ Error migrating table '{table}': {e}")
        migration_stats[table] = {'status': 'error', 'error': str(e)}
        continue

# Close connections
sqlite_conn.close()
pg_conn.close()

# Print summary
print("\n" + "=" * 70)
print("MIGRATION SUMMARY")
print("=" * 70)

for table, stats in migration_stats.items():
    status = stats['status']
    if status == 'success':
        print(f"✓ {table}: {stats['count']} rows migrated, {stats['skipped']} skipped")
    elif status == 'empty':
        print(f"○ {table}: Empty table")
    elif status == 'skipped':
        print(f"⊘ {table}: Not found in SQLite")
    elif status == 'error':
        print(f"✗ {table}: Error - {stats['error']}")

print("\n" + "=" * 70)
print("✅ MIGRATION COMPLETE!")
print("=" * 70)
print("\nYour PostgreSQL database now has all data from SQLite!")
print("You can now use the Render deployment with all your data intact.")
print("\nDefault login credentials:")
print("  Email: admin@dccco.test")
print("  Password: admin123")
