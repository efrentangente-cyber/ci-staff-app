#!/usr/bin/env python3
"""
Apply terminology changes:
1. Change "Loan Staff" to "LPS" everywhere
2. Change "Reject" to "Disapprove" 
3. Update database status values
"""

import sqlite3
import os

def update_database():
    """Update database status values from 'rejected' to 'disapproved'"""
    if not os.path.exists('app.db'):
        print("⚠ Database not found - skipping database updates")
        return
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        # Update existing rejected applications to disapproved
        cursor.execute('''
            UPDATE loan_applications 
            SET status = 'disapproved' 
            WHERE status = 'rejected'
        ''')
        
        affected = cursor.rowcount
        conn.commit()
        
        print(f"✓ Updated {affected} application(s) from 'rejected' to 'disapproved'")
        
    except Exception as e:
        print(f"✗ Database update error: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    print("=" * 70)
    print("APPLYING TERMINOLOGY CHANGES")
    print("=" * 70)
    print("\nChanges to apply:")
    print("1. 'Loan Staff' → 'LPS'")
    print("2. 'Reject/Rejected' → 'Disapprove/Disapproved'")
    print("3. Add 'Defer' option to decisions")
    print("4. Add CI staff reassignment functionality")
    print("5. Remove 'Send directly to loan officer' option")
    print("\n" + "=" * 70)
    
    update_database()
    
    print("\n" + "=" * 70)
    print("✅ DATABASE UPDATES COMPLETE")
    print("=" * 70)
    print("\nNext: Code changes will be applied to templates and app.py")

if __name__ == '__main__':
    main()
