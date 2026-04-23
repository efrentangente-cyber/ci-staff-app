#!/usr/bin/env python3
"""
DCCCO Loan Management System - Workflow Verification & Cleanup
Ensures smooth process: LPS → CI/BI → Loan Officer
Removes duplicates and validates data integrity
"""

import sqlite3
import os
from datetime import datetime

DATABASE = 'app.db'

def verify_system():
    """Comprehensive system verification and cleanup"""
    
    print("=" * 80)
    print("DCCCO LOAN MANAGEMENT SYSTEM - WORKFLOW VERIFICATION")
    print("=" * 80)
    print()
    
    if not os.path.exists(DATABASE):
        print("❌ Database not found!")
        return False
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    issues_found = []
    fixes_applied = []
    
    # 1. Check for duplicate loan applications (same member name, active status)
    print("1. Checking for duplicate loan applications...")
    cursor.execute('''
        SELECT member_name, COUNT(*) as count 
        FROM loan_applications 
        WHERE status NOT IN ('approved', 'disapproved')
        GROUP BY LOWER(member_name)
        HAVING count > 1
    ''')
    duplicates = cursor.fetchall()
    
    if duplicates:
        for dup in duplicates:
            issues_found.append(f"Duplicate applications for: {dup['member_name']} ({dup['count']} active)")
            print(f"   ⚠️  Found {dup['count']} active applications for: {dup['member_name']}")
    else:
        print("   ✓ No duplicate applications found")
    
    # 2. Check for orphaned applications (no assigned CI when needed)
    print("\n2. Checking for orphaned applications...")
    cursor.execute('''
        SELECT id, member_name, status 
        FROM loan_applications 
        WHERE needs_ci_interview = 1 
        AND assigned_ci_staff IS NULL 
        AND status = 'submitted'
    ''')
    orphaned = cursor.fetchall()
    
    if orphaned:
        for app in orphaned:
            issues_found.append(f"Application #{app['id']} ({app['member_name']}) has no CI assigned")
            print(f"   ⚠️  Application #{app['id']} - {app['member_name']} has no CI assigned")
            
            # Auto-assign to available CI
            cursor.execute('''
                SELECT id FROM users 
                WHERE role='ci_staff' AND is_approved=1
                ORDER BY current_workload ASC 
                LIMIT 1
            ''')
            ci = cursor.fetchone()
            
            if ci:
                cursor.execute('''
                    UPDATE loan_applications 
                    SET status='assigned_to_ci', assigned_ci_staff=? 
                    WHERE id=?
                ''', (ci['id'], app['id']))
                cursor.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?', (ci['id'],))
                fixes_applied.append(f"Auto-assigned application #{app['id']} to CI staff")
                print(f"   ✓ Auto-assigned to CI staff (ID: {ci['id']})")
    else:
        print("   ✓ No orphaned applications found")
    
    # 3. Check for stuck applications (assigned but not completed)
    print("\n3. Checking for stuck applications...")
    cursor.execute('''
        SELECT id, member_name, status, submitted_at 
        FROM loan_applications 
        WHERE status = 'assigned_to_ci'
        AND julianday('now') - julianday(submitted_at) > 30
    ''')
    stuck = cursor.fetchall()
    
    if stuck:
        for app in stuck:
            issues_found.append(f"Application #{app['id']} stuck in CI for >30 days")
            print(f"   ⚠️  Application #{app['id']} - {app['member_name']} stuck for >30 days")
    else:
        print("   ✓ No stuck applications found")
    
    # 4. Verify workflow status transitions
    print("\n4. Verifying workflow status transitions...")
    cursor.execute('''
        SELECT id, member_name, status, assigned_ci_staff, ci_completed_at, admin_decision_at
        FROM loan_applications
    ''')
    applications = cursor.fetchall()
    
    workflow_issues = 0
    for app in applications:
        # Check: If status is 'ci_completed', must have ci_completed_at
        if app['status'] == 'ci_completed' and not app['ci_completed_at']:
            issues_found.append(f"Application #{app['id']} marked CI completed but no timestamp")
            workflow_issues += 1
        
        # Check: If status is 'approved' or 'disapproved', must have admin_decision_at
        if app['status'] in ['approved', 'disapproved'] and not app['admin_decision_at']:
            issues_found.append(f"Application #{app['id']} has decision but no timestamp")
            workflow_issues += 1
        
        # Check: If status is 'assigned_to_ci', must have assigned_ci_staff
        if app['status'] == 'assigned_to_ci' and not app['assigned_ci_staff']:
            issues_found.append(f"Application #{app['id']} assigned to CI but no CI staff ID")
            workflow_issues += 1
    
    if workflow_issues == 0:
        print("   ✓ All workflow transitions are valid")
    else:
        print(f"   ⚠️  Found {workflow_issues} workflow issues")
    
    # 5. Check user roles and permissions
    print("\n5. Verifying user roles and permissions...")
    cursor.execute('SELECT id, email, name, role, is_approved FROM users')
    users = cursor.fetchall()
    
    role_issues = 0
    for user in users:
        # Check: All users should have valid roles
        if user['role'] not in ['admin', 'loan_officer', 'loan_staff', 'ci_staff']:
            issues_found.append(f"User {user['email']} has invalid role: {user['role']}")
            role_issues += 1
        
        # Check: All users should be approved for production
        if not user['is_approved']:
            print(f"   ⚠️  User {user['email']} is not approved")
    
    if role_issues == 0:
        print("   ✓ All user roles are valid")
    else:
        print(f"   ⚠️  Found {role_issues} role issues")
    
    # 6. Check for missing documents
    print("\n6. Checking for applications without documents...")
    cursor.execute('''
        SELECT la.id, la.member_name, COUNT(d.id) as doc_count
        FROM loan_applications la
        LEFT JOIN documents d ON la.id = d.loan_application_id
        WHERE la.status NOT IN ('approved', 'disapproved')
        GROUP BY la.id
        HAVING doc_count = 0
    ''')
    no_docs = cursor.fetchall()
    
    if no_docs:
        for app in no_docs:
            print(f"   ⚠️  Application #{app['id']} - {app['member_name']} has no documents")
    else:
        print("   ✓ All active applications have documents")
    
    # 7. Verify CI workload counts
    print("\n7. Verifying CI workload counts...")
    cursor.execute('''
        SELECT u.id, u.name, u.current_workload,
               COUNT(la.id) as actual_workload
        FROM users u
        LEFT JOIN loan_applications la ON u.id = la.assigned_ci_staff 
            AND la.status IN ('assigned_to_ci', 'ci_completed')
        WHERE u.role = 'ci_staff'
        GROUP BY u.id
    ''')
    ci_workloads = cursor.fetchall()
    
    workload_issues = 0
    for ci in ci_workloads:
        if ci['current_workload'] != ci['actual_workload']:
            issues_found.append(f"CI {ci['name']} workload mismatch: stored={ci['current_workload']}, actual={ci['actual_workload']}")
            workload_issues += 1
            
            # Fix workload count
            cursor.execute('UPDATE users SET current_workload = ? WHERE id = ?', 
                         (ci['actual_workload'], ci['id']))
            fixes_applied.append(f"Fixed workload for CI {ci['name']}")
            print(f"   ✓ Fixed workload for {ci['name']}: {ci['current_workload']} → {ci['actual_workload']}")
    
    if workload_issues == 0:
        print("   ✓ All CI workload counts are accurate")
    
    # 8. Check database schema integrity
    print("\n8. Verifying database schema...")
    required_columns = {
        'loan_applications': ['id', 'member_name', 'status', 'lps_remarks', 'assigned_ci_staff'],
        'users': ['id', 'email', 'role', 'is_approved', 'current_workload'],
        'documents': ['id', 'loan_application_id', 'file_name', 'file_path']
    }
    
    schema_issues = 0
    for table, columns in required_columns.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        for col in columns:
            if col not in existing_columns:
                issues_found.append(f"Missing column '{col}' in table '{table}'")
                schema_issues += 1
                print(f"   ❌ Missing column: {table}.{col}")
    
    if schema_issues == 0:
        print("   ✓ Database schema is complete")
    
    # Commit all fixes
    conn.commit()
    conn.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    if issues_found:
        print(f"\n⚠️  Found {len(issues_found)} issues:")
        for issue in issues_found[:10]:  # Show first 10
            print(f"   - {issue}")
        if len(issues_found) > 10:
            print(f"   ... and {len(issues_found) - 10} more")
    else:
        print("\n✓ No issues found - system is clean!")
    
    if fixes_applied:
        print(f"\n✓ Applied {len(fixes_applied)} automatic fixes:")
        for fix in fixes_applied:
            print(f"   - {fix}")
    
    print("\n" + "=" * 80)
    print("WORKFLOW STATUS")
    print("=" * 80)
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Show workflow statistics
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM loan_applications 
        GROUP BY status
    ''')
    statuses = cursor.fetchall()
    
    print("\nApplication Status Distribution:")
    for status in statuses:
        print(f"   {status['status']:20s}: {status['count']:3d} applications")
    
    # Show user statistics
    cursor.execute('''
        SELECT role, COUNT(*) as count, SUM(is_approved) as approved
        FROM users 
        GROUP BY role
    ''')
    roles = cursor.fetchall()
    
    print("\nUser Role Distribution:")
    for role in roles:
        print(f"   {role['role']:20s}: {role['count']:2d} users ({role['approved']} approved)")
    
    conn.close()
    
    print("\n" + "=" * 80)
    
    return len(issues_found) == 0

if __name__ == '__main__':
    success = verify_system()
    
    if success:
        print("\n✅ System is ready for production!")
        print("   Workflow: LPS → CI/BI → Loan Officer is smooth and clean")
    else:
        print("\n⚠️  System has issues that need attention")
        print("   Please review the issues above and take corrective action")
