#!/usr/bin/env python3
"""
Setup PostgreSQL database for Render deployment
This script runs automatically on Render to ensure all tables exist
"""

import os
import sys

def setup_postgresql():
    """Setup PostgreSQL database with all required tables"""
    
    try:
        # Import here to avoid issues if modules not loaded yet
        from database import get_db, get_database_type
        
        db_type = get_database_type()
        print(f"📊 Database type: {db_type.upper()}")
        
        if db_type != 'postgresql':
            print("⚠️  Not using PostgreSQL, skipping setup")
            return
        
        print("🚀 Setting up PostgreSQL database for Render...")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check which tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"✓ Found {len(existing_tables)} existing tables")
        
        # Create loan_types table if missing
        if 'loan_types' not in existing_tables:
            print("📝 Creating loan_types table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_types (
                    id SERIAL PRIMARY KEY,
                    loan_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("   ✓ Created")
        
        # Create system_settings table if missing
        if 'system_settings' not in existing_tables:
            print("📝 Creating system_settings table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    setting_type TEXT DEFAULT 'text',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("   ✓ Created")
        
        # Create sms_templates table if missing
        if 'sms_templates' not in existing_tables:
            print("📝 Creating sms_templates table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sms_templates (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("   ✓ Created")
        
        # Create password_reset_codes table if missing
        if 'password_reset_codes' not in existing_tables:
            print("📝 Creating password_reset_codes table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_codes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
            print("   ✓ Created")
        
        # Create permissions table if missing
        if 'permissions' not in existing_tables:
            print("📝 Creating permissions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    permission_name TEXT NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (granted_by) REFERENCES users(id),
                    UNIQUE(user_id, permission_name)
                )
            """)
            conn.commit()
            print("   ✓ Created")
        
        # Add permissions column to users table if missing
        try:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND table_schema = 'public'
            """)
            user_columns = [row['column_name'] for row in cursor.fetchall()]
            
            if 'permissions' not in user_columns:
                print("📝 Adding permissions column to users...")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT")
                conn.commit()
                print("   ✓ Added")
        except Exception as e:
            print(f"⚠️  Column check/add warning: {e}")
        
        conn.close()
        
        print("✅ PostgreSQL setup complete!")
        print("🎉 Ready to start application!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit with error - let app try to start anyway
        print("⚠️  Continuing despite setup errors...")
        print("⚠️  App will attempt to create tables on first run")

if __name__ == '__main__':
    setup_postgresql()
