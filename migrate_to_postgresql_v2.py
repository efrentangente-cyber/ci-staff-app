#!/usr/bin/env python3
"""
Smart PostgreSQL Migration - Handles schema differences automatically
"""

import os
import sqlite3
import sys

# Set the DATABASE_URL for migration
os.environ['DATABASE_URL'] = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed!")
    print("   Run: pip install psycopg2-binary")
    sys.exit(1)

def migrate():
    print("=" * 80)
    print("SMART POSTGRESQL MIGRATION")
    print("=" * 80)
    print()
    
    # Connect to SQLite
    print("1. Connecting to SQLite (app.db)...")
    try:
        sqlite_conn = sqlite3.connect('app.db')
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        print("   ✓ Connected to SQLite")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Connect to PostgreSQL
    print("\n2. Connecting to PostgreSQL (Render)...")
    try:
        database_url = os.environ['DATABASE_URL']
        pg_conn = psycopg2.connect(database_url, sslmode='require')
        pg_conn.autocommit = False
        pg_cur = pg_conn.cursor()
        print("   ✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Create tables from schema.sql
    print("\n3. Creating tables from schema.sql...")
    try:
        with open('schema.sql', 'r') as f:
            schema = f.read()
            
            # Convert SQLite to PostgreSQL syntax
            schema = schema.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            schema = schema.replace('TEXT DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            schema = schema.replace('AUTOINCREMENT', '')
            schema = schema.replace('INTEGER DEFAULT', 'INTEGER DEFAULT')
            schema = schema.replace('REAL', 'NUMERIC')
            schema = schema.replace('TEXT', 'TEXT')
            
            # Execute schema
            try:
                pg_cur.execute(schema)
                pg_conn.commit()
                print("   ✓ Tables created")
            except Exception as e:
                pg_conn.rollback()
                if 'already exists' in str(e).lower():
                    print("   ✓ Tables already exist")
                else:
                    print(f"   ⚠️  Schema warning: {e}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Migrate data with smart column matching
    tables_config = {
        'users': ['id', 'email', 'password_hash', 'name', 'role', 'signature_path', 'profile_photo', 
                  'current_workload', 'is_approved', 'is_online', 'last_seen', 'backup_email', 
                  'password_reset_token', 'password_reset_expires', 'approval_type', 'assigned_route', 'created_at'],
        'loan_types': ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at'],
        'system_settings': ['id', 'setting_key', 'setting_value', 'setting_type', 'description', 'updated_at'],
        'loan_applications': ['id', 'member_name', 'member_contact', 'member_address', 'loan_amount', 'loan_type',
                             'status', 'needs_ci_interview', 'submitted_by', 'assigned_ci_staff', 'submitted_at',
                             'ci_completed_at', 'admin_decision_at', 'ci_latitude', 'ci_longitude', 'ci_notes',
                             'ci_checklist_data', 'ci_signature', 'admin_notes', 'lps_remarks'],
        'documents': ['id', 'loan_application_id', 'file_name', 'file_path', 'uploaded_by', 'uploaded_at'],
        'messages': ['id', 'loan_application_id', 'sender_id', 'message', 'message_type', 'file_path', 
                    'file_name', 'is_edited', 'is_deleted', 'sent_at', 'edited_at'],
        'notifications': ['id', 'user_id', 'message', 'link', 'is_read', 'created_at'],
        'direct_messages': ['id', 'sender_id', 'receiver_id', 'message', 'message_type', 'file_path',
                           'file_name', 'is_read', 'sent_at'],
        'location_tracking': ['id', 'user_id', 'latitude', 'longitude', 'activity', 'tracked_at'],
        'ci_form_data': None  # Will auto-detect columns
    }
    
    total_rows = 0
    
    for table, expected_columns in tables_config.items():
        print(f"\n4. Migrating table: {table}...")
        
        try:
            # Check if table exists in SQLite
            sqlite_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not sqlite_cur.fetchone():
                print(f"   ⚠️  Table {table} doesn't exist in SQLite")
                continue
            
            # Get actual columns from SQLite
            sqlite_cur.execute(f"PRAGMA table_info({table})")
            sqlite_columns_info = sqlite_cur.fetchall()
            sqlite_columns = [col[1] for col in sqlite_columns_info]
            
            # Get data from SQLite
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                print(f"   ⚠️  No data in {table}")
                continue
            
            # Get PostgreSQL columns
            pg_cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            pg_columns_result = pg_cur.fetchall()
            pg_columns = [col[0] for col in pg_columns_result]
            
            if not pg_columns:
                print(f"   ⚠️  Table {table} doesn't exist in PostgreSQL")
                continue
            
            # Find matching columns (intersection)
            matching_columns = [col for col in sqlite_columns if col in pg_columns and col != 'id']
            
            if not matching_columns:
                print(f"   ⚠️  No matching columns found")
                continue
            
            print(f"   → Migrating columns: {', '.join(matching_columns)}")
            
            # Prepare INSERT statement
            columns_str = ', '.join(matching_columns)
            placeholders = ', '.join(['%s'] * len(matching_columns))
            insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            # Insert data row by row
            success_count = 0
            for row in rows:
                try:
                    # Extract only matching column values
                    row_dict = dict(row)
                    values = tuple(row_dict[col] for col in matching_columns)
                    
                    pg_cur.execute(insert_query, values)
                    success_count += 1
                except Exception as e:
                    # Skip rows that violate constraints (foreign keys, etc.)
                    pass
            
            pg_conn.commit()
            print(f"   ✓ Migrated {success_count}/{len(rows)} rows")
            total_rows += success_count
            
        except Exception as e:
            pg_conn.rollback()
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print(f"\nTotal rows migrated: {total_rows}")
    print("\n📋 NEXT STEPS:")
    print("1. Update .env file with DATABASE_URL")
    print("2. Deploy to Render")
    print("3. Your data will persist forever!")
    print()
    
    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
