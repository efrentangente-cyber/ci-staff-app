#!/usr/bin/env python3
"""
Migration script to add assigned_route column to users table
Run this once to update existing database
"""

import sqlite3

DATABASE = 'app.db'

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'assigned_route' not in columns:
            print("Adding assigned_route column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN assigned_route TEXT")
            conn.commit()
            print("✓ Migration successful! assigned_route column added.")
        else:
            print("✓ assigned_route column already exists. No migration needed.")
        
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
