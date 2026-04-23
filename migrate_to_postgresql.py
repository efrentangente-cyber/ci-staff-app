#!/usr/bin/env python3
"""
Migrate SQLite data to PostgreSQL
Run this ONCE to copy all your local data to Render PostgreSQL
"""

import os
import sqlite3
import sys

# Set the DATABASE_URL for migration
os.environ['DATABASE_URL'] = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 not installed!")
    print("   Run: pip install psycopg2-binary")
    sys.exit(1)

def migrate():
    print("=" * 80)
    print("MIGRATING SQLITE → POSTGRESQL")
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
        print(f"   ❌ Failed to connect to SQLite: {e}")
        return False
    
    # Connect to PostgreSQL
    print("\n2. Connecting to PostgreSQL (Render)...")
    try:
        database_url = os.environ['DATABASE_URL']
        # Add SSL requirement for Render
        pg_conn = psycopg2.connect(database_url, sslmode='require')
        pg_cur = pg_conn.cursor()
        print("   ✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ Failed to connect to PostgreSQL: {e}")
        return False
    
    # Create tables in PostgreSQL
    print("\n3. Creating tables in PostgreSQL...")
    try:
        with open('schema.sql', 'r') as f:
            schema = f.read()
            
            # Convert SQLite syntax to PostgreSQL
            schema = schema.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            schema = schema.replace('TEXT DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            schema = schema.replace('AUTOINCREMENT', '')
            
            # Execute each CREATE TABLE statement separately
            statements = schema.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and statement.upper().startswith(('CREATE', 'DROP')):
                    try:
                        pg_cur.execute(statement)
                    except Exception as e:
                        if 'already exists' not in str(e):
                            print(f"   ⚠️  Warning: {e}")
            
            pg_conn.commit()
            print("   ✓ Tables created")
    except Exception as e:
        print(f"   ❌ Failed to create tables: {e}")
        return False
    
    # Migrate data
    tables = [
        'users',
        'loan_types',
        'system_settings',
        'loan_applications',
        'documents',
        'messages',
        'notifications',
        'direct_messages',
        'location_tracking',
        'ci_form_data'
    ]
    
    total_rows = 0
    
    for table in tables:
        print(f"\n4. Migrating table: {table}...")
        try:
            # Get data from SQLite
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                print(f"   ⚠️  No data in {table}")
                continue
            
            # Get column names
            columns = [description[0] for description in sqlite_cur.description]
            
            # Skip 'id' column for SERIAL primary keys
            if 'id' in columns and columns[0] == 'id':
                columns_without_id = columns[1:]
                columns_str = ', '.join(columns_without_id)
                placeholders = ', '.join(['%s'] * len(columns_without_id))
                
                # Prepare data without id
                data = [tuple(row[1:]) for row in rows]
            else:
                columns_str = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                data = [tuple(row) for row in rows]
            
            # Insert into PostgreSQL
            insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            for row_data in data:
                try:
                    pg_cur.execute(insert_query, row_data)
                except Exception as e:
                    print(f"   ⚠️  Error inserting row: {e}")
            
            pg_conn.commit()
            print(f"   ✓ Migrated {len(rows)} rows")
            total_rows += len(rows)
            
        except Exception as e:
            print(f"   ❌ Error migrating {table}: {e}")
            import traceback
            traceback.print_exc()
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 80)
    print(f"\nTotal rows migrated: {total_rows}")
    print("\nYour data is now in PostgreSQL on Render!")
    print("Next step: Deploy your app to Render")
    print()
    
    return True

if __name__ == '__main__':
    success = migrate()
    if not success:
        sys.exit(1)
