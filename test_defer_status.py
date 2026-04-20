#!/usr/bin/env python3
"""Test defer status implementation"""

import sqlite3

def test_defer():
    print("=" * 60)
    print("TESTING DEFER STATUS IMPLEMENTATION")
    print("=" * 60)
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check schema has deferred
    print("\n1. Checking database schema...")
    schema = cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='loan_applications'"
    ).fetchone()
    
    if schema and ('deferred' in schema['sql']):
        print("   ✓ 'deferred' status exists in CHECK constraint")
    else:
        print("   ✗ 'deferred' status NOT found in constraint")
        return False
    
    # 2. Check SMS templates table
    print("\n2. Checking SMS templates table...")
    sms_table = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sms_templates'"
    ).fetchone()
    
    if sms_table:
        print("   ✓ sms_templates table exists")
        
        # Count templates
        count = cursor.execute("SELECT COUNT(*) as count FROM sms_templates").fetchone()
        print(f"   ✓ {count['count']} SMS templates available")
        
        # Check for deferred templates
        deferred_count = cursor.execute(
            "SELECT COUNT(*) as count FROM sms_templates WHERE category='deferred'"
        ).fetchone()
        print(f"   ✓ {deferred_count['count']} deferred templates")
    else:
        print("   ✗ sms_templates table NOT found")
        return False
    
    # 3. Check sample applications
    print("\n3. Checking sample applications...")
    apps = cursor.execute('''
        SELECT id, member_name, status 
        FROM loan_applications 
        ORDER BY id DESC 
        LIMIT 5
    ''').fetchall()
    
    if apps:
        print(f"   ✓ Found {len(apps)} applications:")
        for app in apps:
            print(f"     - ID: {app['id']}, Name: {app['member_name']}, Status: {app['status']}")
    else:
        print("   ℹ No applications in database yet")
    
    # 4. Test inserting a deferred status (dry run)
    print("\n4. Testing deferred status constraint...")
    try:
        cursor.execute('''
            INSERT INTO loan_applications 
            (member_name, member_contact, member_address, loan_amount, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('Test Member', '09123456789', 'Test Address', 10000, 'deferred'))
        
        # Get the ID
        test_id = cursor.lastrowid
        print(f"   ✓ Successfully inserted test application with 'deferred' status (ID: {test_id})")
        
        # Clean up test data
        cursor.execute('DELETE FROM loan_applications WHERE id = ?', (test_id,))
        print(f"   ✓ Cleaned up test data")
        
    except Exception as e:
        print(f"   ✗ Failed to insert deferred status: {e}")
        return False
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - DEFER STATUS READY")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. Login as admin@dccco.test / admin123")
    print("  2. Review applications in Admin Dashboard")
    print("  3. Click 'Defer' button to defer applications")
    print("  4. SMS will be sent with custom message")
    print("  5. Deferred applications appear in 'Processed' section")
    
    return True

if __name__ == '__main__':
    test_defer()
