#!/usr/bin/env python3
"""
EMERGENCY FIX - Run this directly on Render to create missing tables
This bypasses the normal startup process
"""

import os
import sys

# Set DATABASE_URL if not already set
if 'DATABASE_URL' not in os.environ:
    print("ERROR: DATABASE_URL not set!")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ['DATABASE_URL']
    
    # Fix postgres:// to postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print("🔧 EMERGENCY FIX - Connecting to PostgreSQL...")
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor, sslmode='require')
    cursor = conn.cursor()
    
    print("✓ Connected!")
    
    # Create all missing tables with IF NOT EXISTS
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS loan_types (
            id SERIAL PRIMARY KEY,
            loan_name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            id SERIAL PRIMARY KEY,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'text',
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sms_templates (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            permission_name TEXT NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            granted_by INTEGER,
            UNIQUE(user_id, permission_name)
        )
        """
    ]
    
    for i, sql in enumerate(tables_sql, 1):
        try:
            print(f"Creating table {i}/5...")
            cursor.execute(sql)
            conn.commit()
            print(f"  ✓ Table {i} created")
        except Exception as e:
            print(f"  ⚠️  Table {i} warning: {e}")
            conn.rollback()
    
    # Add permissions column to users if missing
    try:
        print("Adding permissions column to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT")
        conn.commit()
        print("  ✓ Column added")
    except Exception as e:
        print(f"  ⚠️  Column warning: {e}")
        conn.rollback()
    
    conn.close()
    
    print("\n✅ EMERGENCY FIX COMPLETE!")
    print("🎉 Your app should work now!")
    
except Exception as e:
    print(f"\n❌ EMERGENCY FIX FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
