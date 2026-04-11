#!/usr/bin/env python3
"""
Migration script to add loan_type column to loan_applications table
Run this script once to update existing database
"""

import sqlite3
import os

def migrate_database():
    db_path = 'app.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(loan_applications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'loan_type' in columns:
            print("✓ Column 'loan_type' already exists in loan_applications table")
            conn.close()
            return True
        
        # Add the loan_type column
        print("Adding 'loan_type' column to loan_applications table...")
        cursor.execute('''
            ALTER TABLE loan_applications 
            ADD COLUMN loan_type TEXT
        ''')
        
        conn.commit()
        print("✓ Successfully added 'loan_type' column")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(loan_applications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'loan_type' in columns:
            print("✓ Migration completed successfully!")
            conn.close()
            return True
        else:
            print("✗ Migration failed - column not found after adding")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("LOAN TYPE COLUMN MIGRATION")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("Migration completed successfully!")
        print("You can now use the loan_type field in your application.")
    else:
        print("Migration failed. Please check the errors above.")
    print("=" * 60)
