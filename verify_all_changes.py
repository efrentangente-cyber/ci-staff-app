#!/usr/bin/env python3
"""Verify all terminology changes were applied correctly"""

import os
import sqlite3

def check_file_content(filepath, search_terms, should_exist=True):
    """Check if terms exist or don't exist in file"""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = []
    for term in search_terms:
        exists = term in content
        if should_exist and exists:
            results.append(f"✓ Found: '{term}'")
        elif not should_exist and not exists:
            results.append(f"✓ Not found (correct): '{term}'")
        elif should_exist and not exists:
            results.append(f"✗ Missing: '{term}'")
        else:
            results.append(f"✗ Still exists (should be removed): '{term}'")
    
    return all('✓' in r for r in results), results

def main():
    print("=" * 70)
    print("VERIFYING ALL TERMINOLOGY CHANGES")
    print("=" * 70)
    
    all_passed = True
    
    # 1. Check LPS changes
    print("\n1. Checking 'LPS' replacements...")
    passed, results = check_file_content('templates/admin_dashboard.html', ['<th>LPS</th>'], True)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    # 2. Check disapprove changes
    print("\n2. Checking 'Disapprove' changes...")
    passed, results = check_file_content('templates/admin_application.html', 
                                        ['<option value="disapproved">Disapprove</option>'], True)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    # 3. Check defer option
    print("\n3. Checking 'Defer' option...")
    passed, results = check_file_content('templates/admin_application.html', 
                                        ['<option value="deferred">Defer</option>'], True)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    # 4. Check reassignment feature
    print("\n4. Checking CI reassignment feature...")
    passed, results = check_file_content('templates/admin_application.html', 
                                        ['Reassign', 'reassignModal'], True)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    passed, results = check_file_content('app.py', ['def reassign_ci_staff'], True)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    # 5. Check direct to loan officer removed
    print("\n5. Checking 'Send directly' option removed...")
    passed, results = check_file_content('templates/submit_application.html', 
                                        ['Send directly to Loan Officer'], False)
    for r in results:
        print(f"   {r}")
    all_passed = all_passed and passed
    
    # 6. Check database
    print("\n6. Checking database schema...")
    if os.path.exists('app.db'):
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check for disapproved status
        cursor.execute("SELECT COUNT(*) FROM loan_applications WHERE status='disapproved'")
        count = cursor.fetchone()[0]
        print(f"   ✓ Found {count} application(s) with 'disapproved' status")
        
        # Check for old rejected status
        cursor.execute("SELECT COUNT(*) FROM loan_applications WHERE status='rejected'")
        count = cursor.fetchone()[0]
        if count == 0:
            print(f"   ✓ No applications with old 'rejected' status")
        else:
            print(f"   ✗ Still {count} application(s) with 'rejected' status")
            all_passed = False
        
        conn.close()
    else:
        print("   ⚠ Database not found - skipping database checks")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED")
    else:
        print("❌ SOME VERIFICATIONS FAILED")
    print("=" * 70)

if __name__ == '__main__':
    main()
