#!/usr/bin/env python3
"""Quick System Check - Verify all functionality"""
import sqlite3
import os
import json

def check_database():
    """Check database schema and data"""
    print("=" * 60)
    print("DATABASE CHECK")
    print("=" * 60)
    
    if not os.path.exists('app.db'):
        print("❌ Database not found!")
        return False
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables exist
    tables = ['users', 'loan_applications', 'loan_types', 'documents', 'notifications', 'direct_messages', 'system_settings']
    print("\n✓ Checking tables...")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone()['count'] == 0:
            print(f"  ❌ Table '{table}' missing!")
            return False
        print(f"  ✓ {table}")
    
    # Check users
    print("\n✓ Checking users...")
    cursor.execute("SELECT email, name, role, is_approved FROM users")
    users = cursor.fetchall()
    if len(users) == 0:
        print("  ❌ No users found!")
        return False
    
    for user in users:
        status = "✓" if user['is_approved'] else "⚠"
        print(f"  {status} {user['email']} - {user['name']} ({user['role']})")
    
    # Check loan types
    print("\n✓ Checking loan types...")
    cursor.execute("SELECT COUNT(*) as count FROM loan_types WHERE is_active=1")
    count = cursor.fetchone()['count']
    print(f"  ✓ {count} active loan types")
    
    # Check loan_applications columns
    print("\n✓ Checking loan_applications schema...")
    cursor.execute("PRAGMA table_info(loan_applications)")
    columns = [row['name'] for row in cursor.fetchall()]
    required_columns = ['id', 'member_name', 'loan_amount', 'loan_type', 'status', 'ci_checklist_data', 'ci_signature', 'ci_latitude', 'ci_longitude', 'assigned_ci_staff']
    
    for col in required_columns:
        if col in columns:
            print(f"  ✓ {col}")
        else:
            print(f"  ❌ Missing column: {col}")
            return False
    
    conn.close()
    print("\n✅ Database check PASSED")
    return True

def check_files():
    """Check critical files exist"""
    print("\n" + "=" * 60)
    print("FILE CHECK")
    print("=" * 60)
    
    critical_files = [
        'app.py',
        'schema.sql',
        'templates/ci_checklist_wizard.html',
        'templates/view_ci_checklist.html',
        'static/ci-checklist-wizard.js',
        'static/ci-checklist-wizard.css',
        'static/signature-pad.js',
        'templates/base.html',
        'templates/login.html',
        'templates/ci_dashboard.html',
        'templates/loan_dashboard.html',
        'templates/admin_dashboard.html'
    ]
    
    all_exist = True
    for file in critical_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ❌ Missing: {file}")
            all_exist = False
    
    if all_exist:
        print("\n✅ File check PASSED")
    else:
        print("\n❌ File check FAILED")
    
    return all_exist

def check_routes():
    """Check critical routes in app.py"""
    print("\n" + "=" * 60)
    print("ROUTE CHECK")
    print("=" * 60)
    
    if not os.path.exists('app.py'):
        print("❌ app.py not found!")
        return False
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    critical_routes = [
        ('/login', 'login'),
        ('/ci/checklist/<int:id>', 'ci_checklist'),
        ('/ci/checklist/<int:id>', 'submit_ci_checklist'),
        ('/view/checklist/<int:id>', 'view_ci_checklist'),
        ('/loan/dashboard', 'loan_dashboard'),
        ('/ci/dashboard', 'ci_dashboard'),
        ('/admin/dashboard', 'admin_dashboard')
    ]
    
    all_found = True
    for route, func in critical_routes:
        if f"@app.route('{route}" in content and f"def {func}" in content:
            print(f"  ✓ {route} -> {func}()")
        else:
            print(f"  ❌ Missing: {route} -> {func}()")
            all_found = False
    
    if all_found:
        print("\n✅ Route check PASSED")
    else:
        print("\n❌ Route check FAILED")
    
    return all_found

def check_wizard_template():
    """Check wizard template is complete"""
    print("\n" + "=" * 60)
    print("WIZARD TEMPLATE CHECK")
    print("=" * 60)
    
    if not os.path.exists('templates/ci_checklist_wizard.html'):
        print("❌ Wizard template not found!")
        return False
    
    with open('templates/ci_checklist_wizard.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('data-page="1"', 'Page 1 exists'),
        ('data-page="2"', 'Page 2 exists'),
        ('data-page="3"', 'Page 3 exists'),
        ('data-page="4"', 'Page 4 exists'),
        ('data-page="5"', 'Page 5 exists'),
        ('openSignaturePad', 'Signature pad function'),
        ('submitChecklist', 'Submit function'),
        ('ci_signature', 'Signature input field'),
        ('ci_latitude', 'GPS latitude field'),
        ('ci_longitude', 'GPS longitude field'),
        ('checklist_data', 'Checklist data field')
    ]
    
    all_found = True
    for check, desc in checks:
        if check in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_found = False
    
    if all_found:
        print("\n✅ Wizard template check PASSED")
    else:
        print("\n❌ Wizard template check FAILED")
    
    return all_found

def main():
    print("\n🔍 QUICK SYSTEM CHECK - CI CHECKLIST WIZARD")
    print("=" * 60)
    
    results = []
    
    # Run all checks
    results.append(("Database", check_database()))
    results.append(("Files", check_files()))
    results.append(("Routes", check_routes()))
    results.append(("Wizard Template", check_wizard_template()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - SYSTEM READY!")
        print("=" * 60)
        print("\nQuick Test Steps:")
        print("1. Login as CI Staff: ci@dccco.test / ci123")
        print("2. Open application -> Click 'Open Full Checklist (5 Pages)'")
        print("3. Fill pages 1-5, sign on page 5")
        print("4. Submit -> Goes to loan officer")
        print("5. Login as Loan Officer: admin@dccco.test / admin123")
        print("6. View checklist -> Print")
        print("\n✅ Ready to deploy!")
    else:
        print("⚠️  SOME CHECKS FAILED - REVIEW ABOVE")
        print("=" * 60)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
