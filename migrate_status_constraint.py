#!/usr/bin/env python3
"""
Migrate database to update status constraint
Adds 'disapproved' and 'deferred' to allowed status values
"""

import sqlite3
import os

def migrate():
    if not os.path.exists('app.db'):
        print("✗ Database not found")
        return False
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        print("=" * 70)
        print("MIGRATING STATUS CONSTRAINT")
        print("=" * 70)
        
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        print("\n1. Creating backup of loan_applications...")
        cursor.execute('''
            CREATE TABLE loan_applications_backup AS 
            SELECT * FROM loan_applications
        ''')
        print("   ✓ Backup created")
        
        print("\n2. Dropping old table...")
        cursor.execute('DROP TABLE loan_applications')
        print("   ✓ Old table dropped")
        
        print("\n3. Creating new table with updated constraint...")
        cursor.execute('''
            CREATE TABLE loan_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL,
                member_contact TEXT,
                member_address TEXT,
                loan_amount REAL,
                loan_type TEXT,
                status TEXT DEFAULT 'submitted' CHECK(status IN ('submitted', 'assigned_to_ci', 'ci_completed', 'approved', 'disapproved', 'deferred')),
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
        print("   ✓ New table created")
        
        print("\n4. Restoring data...")
        cursor.execute('''
            INSERT INTO loan_applications 
            SELECT * FROM loan_applications_backup
        ''')
        print("   ✓ Data restored")
        
        print("\n5. Dropping backup table...")
        cursor.execute('DROP TABLE loan_applications_backup')
        print("   ✓ Backup dropped")
        
        conn.commit()
        
        # Verify
        print("\n6. Verifying migration...")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='loan_applications'")
        schema = cursor.fetchone()[0]
        
        if 'disapproved' in schema and 'deferred' in schema:
            print("   ✓ Schema updated successfully")
            print("   ✓ Allowed statuses: submitted, assigned_to_ci, ci_completed, approved, disapproved, deferred")
        else:
            print("   ✗ Schema update failed")
            conn.rollback()
            return False
        
        # Check data
        cursor.execute("SELECT COUNT(*) FROM loan_applications")
        count = cursor.fetchone()[0]
        print(f"   ✓ {count} application(s) preserved")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    migrate()
