"""
Setup PostgreSQL database for Render deployment
This script runs automatically on Render to ensure all tables exist
"""

from database import get_db, get_database_type
import sys
import os

def setup_postgresql():
    """Setup PostgreSQL database with all required tables"""
    
    db_type = get_database_type()
    print(f"📊 Database type: {db_type.upper()}")
    
    if db_type != 'postgresql':
        print("⚠️  Not using PostgreSQL, skipping setup")
        return
    
    print("🚀 Setting up PostgreSQL database for Render...")
    
    try:
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
                CREATE TABLE loan_types (
                    id SERIAL PRIMARY KEY,
                    loan_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Created")
        
        # Create system_settings table if missing
        if 'system_settings' not in existing_tables:
            print("📝 Creating system_settings table...")
            cursor.execute("""
                CREATE TABLE system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    setting_type TEXT DEFAULT 'text',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Created")
        
        # Create sms_templates table if missing
        if 'sms_templates' not in existing_tables:
            print("📝 Creating sms_templates table...")
            cursor.execute("""
                CREATE TABLE sms_templates (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Created")
        
        # Create password_reset_codes table if missing
        if 'password_reset_codes' not in existing_tables:
            print("📝 Creating password_reset_codes table...")
            cursor.execute("""
                CREATE TABLE password_reset_codes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            print("   ✓ Created")
        
        # Create permissions table if missing
        if 'permissions' not in existing_tables:
            print("📝 Creating permissions table...")
            cursor.execute("""
                CREATE TABLE permissions (
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
            print("   ✓ Created")
        
        # Add permissions column to users table if missing
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public'
        """)
        user_columns = [row['column_name'] for row in cursor.fetchall()]
        
        if 'permissions' not in user_columns:
            print("📝 Adding permissions column to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
            print("   ✓ Added")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("✅ PostgreSQL setup complete!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    setup_postgresql()
