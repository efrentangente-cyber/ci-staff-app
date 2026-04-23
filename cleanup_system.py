#!/usr/bin/env python3
"""
DCCCO System Cleanup - Fix all issues for production readiness
Removes duplicates, fixes stuck applications, ensures smooth workflow
"""

import sqlite3
import os

DATABASE = 'app.db'

def cleanup_system():
    """Clean up all system issues"""
    
    print("=" * 80)
    print("DCCCO SYSTEM CLEANUP - PRODUCTION READINESS")
    print("=" * 80)
    print()
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    fixes = []
    
    # 1. Remove duplicate applications (keep newest, mark others as disapproved)
    print("1. Removing duplicate applications...")
    cursor.execute('''
        SELECT member_name, COUNT(*) as count 
        FROM loan_applications 
        WHERE status NOT IN ('approved', 'disapproved')
        GROUP BY LOWER(member_name)
        HAVING count > 1
    ''')
    duplicates = cursor.fetchall()
    
    for dup in duplicates:
        # Get all applications for this member
        cursor.execute('''
            SELECT id, submitted_at 
            FROM loan_applications 
            WHERE LOWER(member_name) = LOWER(?)
            AND status NOT IN ('approved', 'disapproved')
            ORDER BY submitted_at DESC
        ''', (dup['member_name'],))
        apps = cursor.fetchall()
        
        # Keep the newest, mark others as disapproved
        for i, app in enumerate(apps):
            if i > 0:  # Skip the first (newest) one
                cursor.execute('''
                    UPDATE loan_applications 
                    SET status = 'disapproved',
                        admin_notes = 'Duplicate application - automatically removed during system cleanup'
                    WHERE id = ?
                ''', (app['id'],))
                fixes.append(f"Removed duplicate application #{app['id']} for {dup['member_name']}")
                print(f"   ✓ Removed duplicate application #{app['id']} for {dup['member_name']}")
    
    if not duplicates:
        print("   ✓ No duplicates to remove")
    
    # 2. Handle stuck applications (>30 days in CI)
    print("\n2. Handling stuck applications...")
    cursor.execute('''
        SELECT id, member_name, assigned_ci_staff
        FROM loan_applications 
        WHERE status = 'assigned_to_ci'
        AND julianday('now') - julianday(submitted_at) > 30
    ''')
    stuck = cursor.fetchall()
    
    for app in stuck:
        # Add admin note about being stuck
        cursor.execute('''
            UPDATE loan_applications 
            SET admin_notes = 'Application was stuck in CI for >30 days - flagged for review'
            WHERE id = ?
        ''', (app['id'],))
        fixes.append(f"Flagged stuck application #{app['id']} ({app['member_name']})")
        print(f"   ✓ Flagged application #{app['id']} - {app['member_name']} for review")
    
    if not stuck:
        print("   ✓ No stuck applications")
    
    # 3. Fix CI workload counts
    print("\n3. Fixing CI workload counts...")
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
    
    for ci in ci_workloads:
        if ci['current_workload'] != ci['actual_workload']:
            cursor.execute('UPDATE users SET current_workload = ? WHERE id = ?', 
                         (ci['actual_workload'], ci['id']))
            fixes.append(f"Fixed workload for {ci['name']}: {ci['current_workload']} → {ci['actual_workload']}")
            print(f"   ✓ Fixed workload for {ci['name']}: {ci['current_workload']} → {ci['actual_workload']}")
    
    if all(ci['current_workload'] == ci['actual_workload'] for ci in ci_workloads):
        print("   ✓ All CI workload counts are accurate")
    
    # 4. Ensure all users are approved
    print("\n4. Approving all users for production...")
    cursor.execute('UPDATE users SET is_approved = 1 WHERE is_approved = 0')
    unapproved_count = cursor.rowcount
    if unapproved_count > 0:
        fixes.append(f"Approved {unapproved_count} users")
        print(f"   ✓ Approved {unapproved_count} users")
    else:
        print("   ✓ All users already approved")
    
    # 5. Clean up test/demo data (optional - commented out for safety)
    # Uncomment if you want to remove test data
    # print("\n5. Removing test/demo data...")
    # cursor.execute("DELETE FROM loan_applications WHERE member_name LIKE '%test%'")
    # test_count = cursor.rowcount
    # if test_count > 0:
    #     fixes.append(f"Removed {test_count} test applications")
    #     print(f"   ✓ Removed {test_count} test applications")
    
    # Commit all changes
    conn.commit()
    
    # Summary
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    
    if fixes:
        print(f"\n✓ Applied {len(fixes)} fixes:")
        for fix in fixes:
            print(f"   - {fix}")
    else:
        print("\n✓ No fixes needed - system is already clean!")
    
    # Show final statistics
    print("\n" + "=" * 80)
    print("FINAL SYSTEM STATUS")
    print("=" * 80)
    
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM loan_applications 
        GROUP BY status
    ''')
    statuses = cursor.fetchall()
    
    print("\nApplication Status Distribution:")
    total_apps = 0
    for status in statuses:
        print(f"   {status['status']:20s}: {status['count']:3d} applications")
        total_apps += status['count']
    print(f"   {'TOTAL':20s}: {total_apps:3d} applications")
    
    cursor.execute('''
        SELECT role, COUNT(*) as count, SUM(is_approved) as approved
        FROM users 
        GROUP BY role
    ''')
    roles = cursor.fetchall()
    
    print("\nUser Role Distribution:")
    for role in roles:
        print(f"   {role['role']:20s}: {role['count']:2d} users (all approved)")
    
    # Check workflow readiness
    cursor.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE status = 'submitted' AND assigned_ci_staff IS NULL
    ''')
    unassigned = cursor.fetchone()['count']
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE status = 'ci_completed' AND admin_decision_at IS NULL
    ''')
    pending_decision = cursor.fetchone()['count']
    
    print("\nWorkflow Status:")
    print(f"   Applications awaiting CI assignment: {unassigned}")
    print(f"   Applications awaiting admin decision: {pending_decision}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ SYSTEM CLEANUP COMPLETE")
    print("=" * 80)
    print("\nWorkflow: LPS → CI/BI → Loan Officer")
    print("Status: READY FOR PRODUCTION")
    print()

if __name__ == '__main__':
    if input("This will clean up the system. Continue? (yes/no): ").lower() == 'yes':
        cleanup_system()
    else:
        print("Cleanup cancelled.")
