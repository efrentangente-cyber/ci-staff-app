"""
Migration Script: Role Restructure & Dynamic Features
- Rename 'admin' role to 'loan_officer'
- Add new 'admin' super role
- Add loan_types table
- Add system_settings table
- Rename latitude/longitude to ci_latitude/ci_longitude in loan_applications
"""

import sqlite3
from werkzeug.security import generate_password_hash

def migrate():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    print("Starting migration...")
    
    try:
        # 1. Update users table - change role constraint
        print("1. Updating users table role constraint...")
        cursor.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'loan_officer', 'loan_staff', 'ci_staff')),
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
        
        # Copy data and rename 'admin' to 'loan_officer'
        cursor.execute('''
            INSERT INTO users_new 
            SELECT id, email, password_hash, name, 
                   CASE WHEN role = 'admin' THEN 'loan_officer' ELSE role END,
                   signature_path, profile_photo, current_workload, is_approved,
                   is_online, last_seen, backup_email, password_reset_token,
                   password_reset_expires, approval_type, assigned_route, created_at
            FROM users
        ''')
        
        cursor.execute('DROP TABLE users')
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        print("   ✓ Users table updated, 'admin' role renamed to 'loan_officer'")
        
        # 2. Create super admin account
        print("2. Creating super admin account...")
        admin_hash = generate_password_hash('admin@2024')
        cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, is_approved)
            VALUES (?, ?, ?, ?, ?)
        ''', ('superadmin@dccco.test', admin_hash, 'Super Admin', 'admin', 1))
        print("   ✓ Super admin created: superadmin@dccco.test / admin@2024")
        
        # 3. Update loan_applications table - rename latitude/longitude
        print("3. Updating loan_applications table...")
        cursor.execute('''
            CREATE TABLE loan_applications_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL,
                member_contact TEXT,
                member_address TEXT,
                loan_amount REAL,
                loan_type TEXT,
                status TEXT DEFAULT 'submitted',
                needs_ci_interview INTEGER DEFAULT 1,
                submitted_by INTEGER,
                assigned_ci_staff INTEGER,
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ci_completed_at TEXT,
                admin_decision_at TEXT,
                ci_latitude REAL,
                ci_longitude REAL,
                ci_notes TEXT,
                ci_checklist_data TEXT,
                ci_signature TEXT,
                admin_notes TEXT,
                FOREIGN KEY (submitted_by) REFERENCES users(id),
                FOREIGN KEY (assigned_ci_staff) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO loan_applications_new
            SELECT id, member_name, member_contact, member_address, loan_amount,
                   loan_type, status, needs_ci_interview, submitted_by, assigned_ci_staff,
                   submitted_at, ci_completed_at, admin_decision_at,
                   latitude, longitude, ci_notes, ci_checklist_data, ci_signature, admin_notes
            FROM loan_applications
        ''')
        
        cursor.execute('DROP TABLE loan_applications')
        cursor.execute('ALTER TABLE loan_applications_new RENAME TO loan_applications')
        print("   ✓ Loan applications table updated")
        
        # 4. Create loan_types table
        print("4. Creating loan_types table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default loan types
        default_loan_types = [
            ('Agricultural with Chattel', 'Agricultural loan with chattel mortgage'),
            ('Agricultural with REM', 'Agricultural loan with real estate mortgage'),
            ('Agricultural w/o Collateral', 'Agricultural loan without collateral'),
            ('Business with Chattel', 'Business loan with chattel mortgage'),
            ('Business with REM', 'Business loan with real estate mortgage'),
            ('Business w/o Collateral', 'Business loan without collateral'),
            ('Multipurpose with Chattel', 'Multipurpose loan with chattel mortgage'),
            ('Multipurpose with REM', 'Multipurpose loan with real estate mortgage'),
            ('Multipurpose w/o Collateral', 'Multipurpose loan without collateral'),
            ('Salary ATM - Dim', 'Salary loan via ATM'),
            ('Salary MOA - Dim', 'Salary loan via MOA'),
            ('Car Loan - Dim (surplus)', 'Car loan for surplus vehicles'),
            ('Car Loan (Brand New) - Dim', 'Car loan for brand new vehicles'),
            ('Back-to-back Loan', 'Back-to-back loan'),
            ('Pension Loan', 'Pension loan'),
            ('Hospitalization Loan', 'Hospitalization loan'),
            ('Petty Cash Loan', 'Petty cash loan'),
            ('Incentive Loan', 'Incentive loan')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO loan_types (name, description)
            VALUES (?, ?)
        ''', default_loan_types)
        print(f"   ✓ Loan types table created with {len(default_loan_types)} default types")
        
        # 5. Create system_settings table
        print("5. Creating system_settings table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type TEXT DEFAULT 'text',
                description TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default settings
        default_settings = [
            ('system_name', 'DCCCO Loan Management System', 'text', 'System name'),
            ('auto_assign_ci', '1', 'boolean', 'Auto-assign CI staff to applications'),
            ('require_ci_interview', '1', 'boolean', 'Require CI interview for all loans'),
            ('location_tracking_enabled', '1', 'boolean', 'Enable GPS location tracking for CI staff'),
            ('location_update_interval', '30', 'number', 'Location update interval in seconds')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value, setting_type, description)
            VALUES (?, ?, ?, ?)
        ''', default_settings)
        print(f"   ✓ System settings table created with {len(default_settings)} default settings")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\n📋 Summary:")
        print("   - Role 'admin' renamed to 'loan_officer'")
        print("   - New super admin account created")
        print("   - Loan types table created with 18 types")
        print("   - System settings table created")
        print("   - Location fields renamed to ci_latitude/ci_longitude")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
