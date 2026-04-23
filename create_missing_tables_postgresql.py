"""
Create missing tables in PostgreSQL database
This script creates tables that don't exist yet
"""

from database import get_db, get_database_type
import sys

def create_missing_tables():
    """Create missing tables in PostgreSQL"""
    
    db_type = get_database_type()
    if db_type != 'postgresql':
        print(f"❌ This script is for PostgreSQL only. Current database: {db_type}")
        sys.exit(1)
    
    print("📊 Creating missing tables in PostgreSQL...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check which tables exist
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    existing_tables = [row['table_name'] for row in cursor.fetchall()]
    print(f"\n✓ Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}")
    
    tables_created = []
    
    # Create loan_types table
    if 'loan_types' not in existing_tables:
        print("\n📝 Creating loan_types table...")
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
        tables_created.append('loan_types')
        print("   ✓ Created loan_types table")
    
    # Create system_settings table
    if 'system_settings' not in existing_tables:
        print("\n📝 Creating system_settings table...")
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
        tables_created.append('system_settings')
        print("   ✓ Created system_settings table")
    
    # Create sms_templates table
    if 'sms_templates' not in existing_tables:
        print("\n📝 Creating sms_templates table...")
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
        tables_created.append('sms_templates')
        print("   ✓ Created sms_templates table")
    
    # Create password_reset_codes table
    if 'password_reset_codes' not in existing_tables:
        print("\n📝 Creating password_reset_codes table...")
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
        tables_created.append('password_reset_codes')
        print("   ✓ Created password_reset_codes table")
    
    # Create permissions table
    if 'permissions' not in existing_tables:
        print("\n📝 Creating permissions table...")
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
        tables_created.append('permissions')
        print("   ✓ Created permissions table")
    
    # Add permissions column to users table if it doesn't exist
    print("\n📝 Checking users table columns...")
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'users' AND table_schema = 'public'
    """)
    user_columns = [row['column_name'] for row in cursor.fetchall()]
    
    if 'permissions' not in user_columns:
        print("   Adding permissions column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
        print("   ✓ Added permissions column")
    
    # Commit all changes
    conn.commit()
    
    print(f"\n✅ Migration complete!")
    print(f"   Tables created: {len(tables_created)}")
    if tables_created:
        for table in tables_created:
            print(f"      - {table}")
    else:
        print("   All tables already exist")
    
    conn.close()

if __name__ == '__main__':
    create_missing_tables()
