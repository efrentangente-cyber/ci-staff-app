#!/usr/bin/env python3
"""
Migration: Add 'deferred' status to loan_applications table
This fixes the Internal Server Error on Render
"""

import sqlite3
import sys

def migrate():
    print("=" * 60)
    print("MIGRATION: Add 'deferred' status to CHECK constraint")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check current schema
        print("\n1. Checking current schema...")
        schema = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='loan_applications'"
        ).fetchone()
        
        if not schema:
            print("   ✗ loan_applications table not found!")
            return False
        
        current_schema = schema[0]
        print("   ✓ Table found")
        
        # Check if deferred already exists
        if "'deferred'" in current_schema or '"deferred"' in current_schema:
            print("   ✓ 'deferred' status already exists in constraint")
            print("\n✓ No migration needed")
            return True
        
        print("   → 'deferred' status NOT found in constraint")
        print("\n2. Creating backup...")
        
        # Create backup table
        cursor.execute('''
            CREATE TABLE loan_applications_backup AS 
            SELECT * FROM loan_applications
        ''')
        
        backup_count = cursor.execute('SELECT COUNT(*) FROM loan_applications_backup').fetchone()[0]
        print(f"   ✓ Backed up {backup_count} records")
        
        print("\n3. Creating new table with updated constraint...")
        
        # Create new table with deferred status
        cursor.execute('''
            CREATE TABLE loan_applications_new (
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
                submitted_at TEXT,
                admin_notes TEXT,
                admin_decision_at TEXT,
                ci_checklist_data TEXT,
                ci_latitude REAL,
                ci_longitude REAL,
                ci_location_timestamp TEXT,
                assigned_route TEXT,
                FOREIGN KEY (submitted_by) REFERENCES users (id),
                FOREIGN KEY (assigned_ci_staff) REFERENCES users (id)
            )
        ''')
        print("   ✓ New table created")
        
        print("\n4. Copying data to new table...")
        
        # Copy all data
        cursor.execute('''
            INSERT INTO loan_applications_new 
            SELECT * FROM loan_applications
        ''')
        
        new_count = cursor.execute('SELECT COUNT(*) FROM loan_applications_new').fetchone()[0]
        print(f"   ✓ Copied {new_count} records")
        
        print("\n5. Replacing old table...")
        
        # Drop old table
        cursor.execute('DROP TABLE loan_applications')
        print("   ✓ Dropped old table")
        
        # Rename new table
        cursor.execute('ALTER TABLE loan_applications_new RENAME TO loan_applications')
        print("   ✓ Renamed new table")
        
        # Commit changes
        conn.commit()
        
        print("\n6. Verifying migration...")
        
        # Verify new schema
        new_schema = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='loan_applications'"
        ).fetchone()[0]
        
        if "'deferred'" in new_schema or '"deferred"' in new_schema:
            print("   ✓ 'deferred' status confirmed in new schema")
        else:
            print("   ✗ 'deferred' status NOT found in new schema!")
            return False
        
        # Verify record count
        final_count = cursor.execute('SELECT COUNT(*) FROM loan_applications').fetchone()[0]
        print(f"   ✓ Final record count: {final_count}")
        
        if final_count == backup_count:
            print("   ✓ All records preserved")
        else:
            print(f"   ✗ Record count mismatch! Backup: {backup_count}, Final: {final_count}")
            return False
        
        # Drop backup table
        cursor.execute('DROP TABLE loan_applications_backup')
        conn.commit()
        print("   ✓ Backup table removed")
        
        print("\n" + "=" * 60)
        print("✓ MIGRATION COMPLETE")
        print("=" * 60)
        print("\nThe 'deferred' status has been added to the database.")
        print("Admin and Loan Officer can now login without errors.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to restore from backup
        try:
            print("\nAttempting to restore from backup...")
            cursor.execute('DROP TABLE IF EXISTS loan_applications')
            cursor.execute('ALTER TABLE loan_applications_backup RENAME TO loan_applications')
            conn.commit()
            print("✓ Restored from backup")
        except:
            print("✗ Could not restore from backup")
        
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
