#!/usr/bin/env python3
"""
Migration: Add SMS Templates Table
Creates table for storing SMS message templates
"""

import sqlite3
import sys

DATABASE = 'app.db'

def migrate():
    """Add sms_templates table"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sms_templates'
        """)
        
        if cursor.fetchone():
            print("✓ sms_templates table already exists")
            conn.close()
            return True
        
        # Create sms_templates table
        cursor.execute("""
            CREATE TABLE sms_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # Insert default templates
        default_templates = [
            (
                'Loan Approved - Standard',
                'approved',
                'Good day {member_name}! Your loan application for {loan_type} amounting to ₱{loan_amount} has been APPROVED. Please visit our office to complete the requirements. - DCCCO',
                1
            ),
            (
                'Loan Approved - With Schedule',
                'approved',
                'Congratulations {member_name}! Your {loan_type} loan of ₱{loan_amount} is APPROVED. Please come to DCCCO office on {date} to process your loan release. Thank you!',
                1
            ),
            (
                'Loan Disapproved - Standard',
                'disapproved',
                'Dear {member_name}, we regret to inform you that your loan application for {loan_type} amounting to ₱{loan_amount} has been DISAPPROVED. Please contact our office for more details. - DCCCO',
                1
            ),
            (
                'Loan Disapproved - Incomplete Requirements',
                'disapproved',
                'Hi {member_name}, your {loan_type} loan application has been DISAPPROVED due to incomplete requirements. Please visit our office to discuss. - DCCCO',
                1
            ),
            (
                'Loan Deferred - Standard',
                'deferred',
                'Dear {member_name}, your loan application for {loan_type} amounting to ₱{loan_amount} has been DEFERRED. We need additional information. Please contact our office. - DCCCO',
                1
            ),
            (
                'Loan Deferred - Pending Documents',
                'deferred',
                'Hi {member_name}, your {loan_type} loan is DEFERRED pending submission of required documents. Please submit them at DCCCO office. Thank you!',
                1
            ),
            (
                'General Reminder',
                'custom',
                'Dear {member_name}, this is a reminder regarding your loan application. Please contact DCCCO office for updates. Thank you!',
                1
            )
        ]
        
        cursor.executemany("""
            INSERT INTO sms_templates (name, category, message, is_active)
            VALUES (?, ?, ?, ?)
        """, default_templates)
        
        conn.commit()
        print("✓ Created sms_templates table")
        print(f"✓ Inserted {len(default_templates)} default templates")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Running SMS Templates migration...")
    success = migrate()
    sys.exit(0 if success else 1)
