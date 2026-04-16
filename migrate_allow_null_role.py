import sqlite3

def migrate():
    """
    Migrate users table to allow NULL role
    This allows new registrations without role, which admin will assign later
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        print("Starting migration to allow NULL role...")
        
        # Step 0: Drop users_new if it exists (cleanup from previous failed attempt)
        cursor.execute('DROP TABLE IF EXISTS users_new')
        print("✓ Cleaned up any previous migration attempts")
        
        # Step 1: Create new table with NULL-able role
        cursor.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'loan_officer', 'loan_staff', 'ci_staff') OR role IS NULL),
                signature_path TEXT,
                profile_photo TEXT,
                current_workload INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 0,
                is_online INTEGER DEFAULT 0,
                last_seen TEXT,
                backup_email TEXT,
                password_reset_token TEXT,
                password_reset_expires TEXT,
                approval_type TEXT,
                assigned_route TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created new users table")
        
        # Step 2: Copy all data from old table to new table
        cursor.execute('''
            INSERT INTO users_new 
            SELECT * FROM users
        ''')
        print("✓ Copied all user data")
        
        # Step 3: Drop old table
        cursor.execute('DROP TABLE users')
        print("✓ Dropped old users table")
        
        # Step 4: Rename new table to users
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        print("✓ Renamed new table to users")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("Users can now register without a role (admin will assign later)")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
