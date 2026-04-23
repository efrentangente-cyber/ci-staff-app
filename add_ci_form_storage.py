#!/usr/bin/env python3
"""
Add CI Form Data Storage
Allows CI staff to save/load form progress and templates
"""

import sqlite3
import os

DATABASE = 'app.db'

def add_ci_form_storage():
    """Add table for CI form data storage"""
    
    print("=" * 80)
    print("Adding CI Form Data Storage")
    print("=" * 80)
    print()
    
    if not os.path.exists(DATABASE):
        print("❌ Database not found!")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ci_form_data'
        """)
        
        if cursor.fetchone():
            print("✓ Table 'ci_form_data' already exists")
            conn.close()
            return True
        
        # Create CI form data storage table
        print("Creating 'ci_form_data' table...")
        cursor.execute('''
            CREATE TABLE ci_form_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                application_id INTEGER,
                form_type TEXT NOT NULL,
                form_data TEXT NOT NULL,
                is_template INTEGER DEFAULT 0,
                template_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (application_id) REFERENCES loan_applications(id)
            )
        ''')
        
        # Create indexes for faster queries
        print("Creating indexes...")
        cursor.execute('''
            CREATE INDEX idx_ci_form_data_user 
            ON ci_form_data(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX idx_ci_form_data_application 
            ON ci_form_data(application_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX idx_ci_form_data_type 
            ON ci_form_data(form_type)
        ''')
        
        conn.commit()
        
        print("✓ Successfully created 'ci_form_data' table")
        print("✓ Created indexes for performance")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(ci_form_data)")
        columns = cursor.fetchall()
        
        print("\nTable Structure:")
        for col in columns:
            print(f"   {col[1]:20s} {col[2]:15s}")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ CI Form Data Storage Added Successfully")
        print("=" * 80)
        print("\nFeatures enabled:")
        print("   - Save form progress")
        print("   - Load saved forms")
        print("   - Create form templates")
        print("   - Auto-fill from previous applications")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    add_ci_form_storage()
