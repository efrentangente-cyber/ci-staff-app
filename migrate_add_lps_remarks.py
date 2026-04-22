#!/usr/bin/env python3
"""
Migration script to add lps_remarks column to loan_applications table
This allows LPS to add remarks/notes when submitting applications
"""

import sqlite3
import os

DATABASE = 'app.db'

def migrate():
    """Add lps_remarks column to loan_applications table"""
    if not os.path.exists(DATABASE):
        print(f"❌ Database {DATABASE} not found!")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(loan_applications)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'lps_remarks' in columns:
            print("✓ Column 'lps_remarks' already exists in loan_applications table")
            conn.close()
            return True
        
        # Add the column
        print("Adding 'lps_remarks' column to loan_applications table...")
        cursor.execute('''
            ALTER TABLE loan_applications 
            ADD COLUMN lps_remarks TEXT
        ''')
        
        conn.commit()
        print("✓ Successfully added 'lps_remarks' column")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(loan_applications)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'lps_remarks' in columns:
            print("✓ Migration verified successfully")
            conn.close()
            return True
        else:
            print("❌ Migration verification failed")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("LPS Remarks Migration")
    print("=" * 60)
    
    success = migrate()
    
    print("=" * 60)
    if success:
        print("✓ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
    print("=" * 60)
