#!/usr/bin/env python3
"""
Migration script to add media support to direct_messages table
Adds: message_type, file_path, file_name columns
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
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(direct_messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add message_type column
        if 'message_type' not in columns:
            print("Adding 'message_type' column...")
            cursor.execute('''
                ALTER TABLE direct_messages 
                ADD COLUMN message_type TEXT DEFAULT 'text'
            ''')
            print("✓ Added message_type column")
        else:
            print("✓ message_type column already exists")
        
        # Add file_path column
        if 'file_path' not in columns:
            print("Adding 'file_path' column...")
            cursor.execute('''
                ALTER TABLE direct_messages 
                ADD COLUMN file_path TEXT
            ''')
            print("✓ Added file_path column")
        else:
            print("✓ file_path column already exists")
        
        # Add file_name column
        if 'file_name' not in columns:
            print("Adding 'file_name' column...")
            cursor.execute('''
                ALTER TABLE direct_messages 
                ADD COLUMN file_name TEXT
            ''')
            print("✓ Added file_name column")
        else:
            print("✓ file_name column already exists")
        
        conn.commit()
        print("\n✓ Migration completed successfully!")
        conn.close()
        return True
            
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("DIRECT MESSAGES MEDIA SUPPORT MIGRATION")
    print("=" * 60)
    print()
    
    migrate_database()
    
    print("=" * 60)
