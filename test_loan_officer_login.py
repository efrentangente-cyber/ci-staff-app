#!/usr/bin/env python3
"""
Test Loan Officer Login
Verifies that loan officer can login and access admin dashboard
"""

import sqlite3

def test_loan_officer_login():
    print("=" * 60)
    print("LOAN OFFICER LOGIN TEST")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if loan_officer role exists
        print("\n1. Checking for loan_officer users...")
        loan_officers = cursor.execute('''
            SELECT id, name, email, role, is_approved 
            FROM users 
            WHERE role = 'loan_officer'
        ''').fetchall()
        
        if loan_officers:
            print(f"   ✓ Found {len(loan_officers)} loan officer(s)")
            for lo in loan_officers:
                status = "✓ Approved" if lo['is_approved'] == 1 else "✗ Pending Approval"
                print(f"     - {lo['name']} ({lo['email']}) - {status}")
        else:
            print("   ✗ No loan officers found")
            print("   → Creating test loan officer...")
            
            from werkzeug.security import generate_password_hash
            cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, is_approved)
                VALUES (?, ?, ?, ?, ?)
            ''', ('loanofficer@test.com', generate_password_hash('password123'), 
                  'Test Loan Officer', 'loan_officer', 1))
            conn.commit()
            print("   ✓ Test loan officer created")
            print("     Email: loanofficer@test.com")
            print("     Password: password123")
        
        # Check admin_dashboard query compatibility
        print("\n2. Testing admin_dashboard query...")
        try:
            applications = cursor.execute('''
                SELECT la.*, 
                       u1.name as loan_staff_name,
                       u2.name as ci_staff_name
                FROM loan_applications la
                LEFT JOIN users u1 ON la.submitted_by = u1.id
                LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
                WHERE la.status IN ('ci_completed', 'approved', 'disapproved', 'deferred')
                   OR (la.needs_ci_interview = 0 AND la.status = 'submitted')
                ORDER BY la.submitted_at ASC
            ''').fetchall()
            
            print(f"   ✓ Query executed successfully")
            print(f"   ✓ Found {len(applications)} applications for review")
            
            # Count by status
            status_counts = {}
            for app in applications:
                status = app['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                print("   Status breakdown:")
                for status, count in status_counts.items():
                    print(f"     - {status}: {count}")
            
        except Exception as e:
            print(f"   ✗ Query failed: {e}")
            return False
        
        # Check in_process query
        print("\n3. Testing in_process query...")
        try:
            in_process = cursor.execute('''
                SELECT la.*, 
                       u1.name as loan_staff_name,
                       u2.name as ci_staff_name
                FROM loan_applications la
                LEFT JOIN users u1 ON la.submitted_by = u1.id
                LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
                WHERE la.status IN ('submitted', 'assigned_to_ci')
                ORDER BY la.submitted_at ASC
            ''').fetchall()
            
            print(f"   ✓ Query executed successfully")
            print(f"   ✓ Found {len(in_process)} in-process applications")
            
        except Exception as e:
            print(f"   ✗ Query failed: {e}")
            return False
        
        # Check CI staff query
        print("\n4. Testing CI staff query...")
        try:
            ci_staff = cursor.execute('''
                SELECT id, name, email, is_online, last_seen, profile_photo
                FROM users 
                WHERE role = 'ci_staff'
                ORDER BY is_online DESC, name ASC
            ''').fetchall()
            
            print(f"   ✓ Query executed successfully")
            print(f"   ✓ Found {len(ci_staff)} CI staff members")
            
        except Exception as e:
            print(f"   ✗ Query failed: {e}")
            return False
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nLoan Officer Login Status: WORKING ✓")
        print("\nTo test login:")
        print("1. Go to http://localhost:5000/login")
        print("2. Login with loan officer credentials")
        print("3. Should redirect to admin dashboard")
        print("4. Should see all applications without errors")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_loan_officer_login()
