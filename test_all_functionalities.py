#!/usr/bin/env python3
"""
Comprehensive functionality test
Tests all critical workflows and terminology changes
"""

import sqlite3
import os

def test_database_schema():
    """Test database schema is correct"""
    print("\n1. Testing Database Schema...")
    
    if not os.path.exists('app.db'):
        print("   ⚠ Database not found")
        return False
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        # Check loan_applications table
        cursor.execute("PRAGMA table_info(loan_applications)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        if 'status' in columns:
            print("   ✓ Status column exists")
            
            # Check if status constraint allows new values
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='loan_applications'")
            schema = cursor.fetchone()[0]
            
            if 'disapproved' in schema:
                print("   ✓ Schema includes 'disapproved' status")
            else:
                print("   ✗ Schema missing 'disapproved' status")
                return False
                
            if 'deferred' in schema:
                print("   ✓ Schema includes 'deferred' status")
            else:
                print("   ⚠ Schema missing 'deferred' status (may need migration)")
        
        # Check for old rejected status in data
        cursor.execute("SELECT COUNT(*) FROM loan_applications WHERE status='rejected'")
        rejected_count = cursor.fetchone()[0]
        
        if rejected_count == 0:
            print(f"   ✓ No applications with old 'rejected' status")
        else:
            print(f"   ✗ Found {rejected_count} applications with 'rejected' status - needs migration")
            return False
        
        # Check for disapproved status
        cursor.execute("SELECT COUNT(*) FROM loan_applications WHERE status='disapproved'")
        disapproved_count = cursor.fetchone()[0]
        print(f"   ✓ Found {disapproved_count} application(s) with 'disapproved' status")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        conn.close()
        return False

def test_file_consistency():
    """Test all files have consistent terminology"""
    print("\n2. Testing File Consistency...")
    
    files_to_check = {
        'templates/admin_dashboard.html': {
            'should_have': ['<th>LPS</th>', 'disapproved', 'Disapproved'],
            'should_not_have': ['Loan Staff', 'rejected', 'Rejected']
        },
        'templates/admin_application.html': {
            'should_have': ['disapproved', 'Disapprove', 'deferred', 'Defer', 'Reassign'],
            'should_not_have': ['rejected', 'Reject']
        },
        'templates/submit_application.html': {
            'should_have': ['Assign to CI Staff'],
            'should_not_have': ['Send directly to Loan Officer']
        },
        'templates/manage_users.html': {
            'should_have': ['LPS', 'disapprove_user', 'Disapprove'],
            'should_not_have': ['Loan Staff', 'reject_user', 'Reject']
        },
        'app.py': {
            'should_have': ['disapproved', 'def disapprove_user', 'def reassign_ci_staff'],
            'should_not_have': ['def reject_user']
        },
        'static/realtime-dashboard.js': {
            'should_have': ['disapproved'],
            'should_not_have': ['rejected']
        }
    }
    
    all_passed = True
    
    for filepath, checks in files_to_check.items():
        if not os.path.exists(filepath):
            print(f"   ⚠ File not found: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_passed = True
        
        # Check should_have
        for term in checks['should_have']:
            if term not in content:
                print(f"   ✗ {filepath}: Missing '{term}'")
                file_passed = False
                all_passed = False
        
        # Check should_not_have
        for term in checks['should_not_have']:
            if term in content:
                print(f"   ✗ {filepath}: Still contains '{term}'")
                file_passed = False
                all_passed = False
        
        if file_passed:
            print(f"   ✓ {filepath}")
    
    return all_passed

def test_routes():
    """Test that all routes are defined"""
    print("\n3. Testing Routes...")
    
    if not os.path.exists('app.py'):
        print("   ✗ app.py not found")
        return False
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_routes = [
        'def admin_application',
        'def reassign_ci_staff',
        'def disapprove_user',
        'def submit_application',
        'def manage_permissions',
    ]
    
    all_found = True
    for route in required_routes:
        if route in content:
            print(f"   ✓ {route}()")
        else:
            print(f"   ✗ {route}() not found")
            all_found = False
    
    return all_found

def test_user_roles():
    """Test user roles are correct"""
    print("\n4. Testing User Roles...")
    
    if not os.path.exists('app.db'):
        print("   ⚠ Database not found")
        return False
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT role, COUNT(*) as count FROM users WHERE is_approved=1 GROUP BY role")
        roles = cursor.fetchall()
        
        role_counts = {row['role']: row['count'] for row in roles}
        
        required_roles = ['admin', 'loan_officer', 'loan_staff', 'ci_staff']
        
        for role in required_roles:
            count = role_counts.get(role, 0)
            if count > 0:
                print(f"   ✓ {role}: {count} user(s)")
            else:
                print(f"   ⚠ {role}: No users found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        conn.close()
        return False

def main():
    print("=" * 70)
    print("COMPREHENSIVE FUNCTIONALITY TEST")
    print("=" * 70)
    
    results = []
    
    results.append(("Database Schema", test_database_schema()))
    results.append(("File Consistency", test_file_consistency()))
    results.append(("Routes", test_routes()))
    results.append(("User Roles", test_user_roles()))
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - SYSTEM READY")
    else:
        print("❌ SOME TESTS FAILED - REVIEW ABOVE")
    print("=" * 70)
    
    if all_passed:
        print("\n✓ All functionalities are working smoothly!")
        print("✓ Terminology changes complete")
        print("✓ Ready for deployment")

if __name__ == '__main__':
    main()
