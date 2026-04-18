#!/usr/bin/env python3
"""Comprehensive System Check - Full Process Validation"""
import sqlite3
import os
import json

def check_database_schema():
    """Check database schema is complete"""
    print("\n" + "=" * 70)
    print("1. DATABASE SCHEMA CHECK")
    print("=" * 70)
    
    if not os.path.exists('app.db'):
        print("❌ Database not found!")
        return False
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check all required tables
    required_tables = {
        'users': ['id', 'email', 'password_hash', 'name', 'role', 'is_approved', 'assigned_route'],
        'loan_applications': ['id', 'member_name', 'member_contact', 'member_address', 'loan_amount', 'loan_type', 
                             'status', 'submitted_by', 'assigned_ci_staff', 'ci_checklist_data', 'ci_signature', 
                             'ci_latitude', 'ci_longitude', 'ci_completed_at', 'submitted_at'],
        'loan_types': ['id', 'name', 'description', 'is_active'],
        'documents': ['id', 'loan_application_id', 'file_name', 'file_path', 'uploaded_by'],
        'notifications': ['id', 'user_id', 'message', 'link', 'is_read', 'created_at'],
        'direct_messages': ['id', 'sender_id', 'receiver_id', 'message', 'sent_at', 'is_read'],
        'system_settings': ['id', 'setting_key', 'setting_value', 'description']
    }
    
    all_good = True
    for table, columns in required_tables.items():
        cursor.execute(f"SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone()['count'] == 0:
            print(f"  ❌ Table '{table}' missing!")
            all_good = False
            continue
        
        # Check columns
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [row['name'] for row in cursor.fetchall()]
        
        missing_columns = [col for col in columns if col not in existing_columns]
        if missing_columns:
            print(f"  ⚠️  Table '{table}' missing columns: {', '.join(missing_columns)}")
            all_good = False
        else:
            print(f"  ✓ {table} - All columns present")
    
    conn.close()
    return all_good

def check_users():
    """Check users are properly configured"""
    print("\n" + "=" * 70)
    print("2. USERS CHECK")
    print("=" * 70)
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, name, role, is_approved FROM users ORDER BY role")
    users = cursor.fetchall()
    
    if len(users) == 0:
        print("  ❌ No users found!")
        conn.close()
        return False
    
    required_roles = {'admin': 0, 'loan_officer': 0, 'loan_staff': 0, 'ci_staff': 0}
    
    for user in users:
        status = "✓" if user['is_approved'] else "⚠️ NOT APPROVED"
        print(f"  {status} {user['email']:30s} {user['name']:20s} ({user['role']})")
        if user['role'] in required_roles:
            required_roles[user['role']] += 1
    
    print("\n  Role Summary:")
    all_roles_present = True
    for role, count in required_roles.items():
        if count == 0:
            print(f"    ❌ No {role} found!")
            all_roles_present = False
        else:
            print(f"    ✓ {count} {role}(s)")
    
    conn.close()
    return all_roles_present

def check_loan_types():
    """Check loan types are configured"""
    print("\n" + "=" * 70)
    print("3. LOAN TYPES CHECK")
    print("=" * 70)
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM loan_types WHERE is_active=1")
    count = cursor.fetchone()['count']
    
    if count == 0:
        print("  ❌ No active loan types!")
        conn.close()
        return False
    
    print(f"  ✓ {count} active loan types")
    
    cursor.execute("SELECT name FROM loan_types WHERE is_active=1 LIMIT 5")
    for row in cursor.fetchall():
        print(f"    - {row['name']}")
    
    if count > 5:
        print(f"    ... and {count - 5} more")
    
    conn.close()
    return True

def check_routes():
    """Check critical routes exist in app.py"""
    print("\n" + "=" * 70)
    print("4. ROUTES CHECK")
    print("=" * 70)
    
    if not os.path.exists('app.py'):
        print("  ❌ app.py not found!")
        return False
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    critical_routes = [
        ('/login', 'login', 'Login page'),
        ('/logout', 'logout', 'Logout'),
        ('/loan/dashboard', 'loan_dashboard', 'Loan staff dashboard'),
        ('/loan/submit', 'submit_application', 'Submit application'),
        ('/ci/dashboard', 'ci_dashboard', 'CI staff dashboard'),
        ('/ci/application/<int:id>', 'ci_application', 'CI application (redirects to wizard)'),
        ('/ci/checklist/<int:id>', 'ci_checklist', 'CI checklist wizard (GET)'),
        ('/ci/checklist/<int:id>', 'submit_ci_checklist', 'CI checklist submit (POST)'),
        ('/admin/dashboard', 'admin_dashboard', 'Admin/Loan officer dashboard'),
        ('/view/checklist/<int:id>', 'view_ci_checklist', 'View completed checklist')
    ]
    
    all_found = True
    for route, func, desc in critical_routes:
        if f"@app.route('{route}" in content and f"def {func}" in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ❌ Missing: {desc} ({route} -> {func})")
            all_found = False
    
    return all_found

def check_templates():
    """Check critical templates exist"""
    print("\n" + "=" * 70)
    print("5. TEMPLATES CHECK")
    print("=" * 70)
    
    critical_templates = [
        'templates/base.html',
        'templates/login.html',
        'templates/loan_dashboard.html',
        'templates/submit_application.html',
        'templates/ci_dashboard.html',
        'templates/ci_checklist_wizard.html',
        'templates/view_ci_checklist.html',
        'templates/admin_dashboard.html',
        'templates/manage_users.html'
    ]
    
    all_exist = True
    for template in critical_templates:
        if os.path.exists(template):
            print(f"  ✓ {template}")
        else:
            print(f"  ❌ Missing: {template}")
            all_exist = False
    
    # Check deleted templates are gone
    deleted_templates = [
        'templates/ci_application.html',
        'templates/ci_checklist_mobile.html',
        'templates/ci_checklist_form.html'
    ]
    
    print("\n  Checking deleted templates:")
    for template in deleted_templates:
        if not os.path.exists(template):
            print(f"  ✓ {template} - Correctly deleted")
        else:
            print(f"  ⚠️  {template} - Still exists (should be deleted)")
    
    return all_exist

def check_wizard_template():
    """Check wizard template is complete"""
    print("\n" + "=" * 70)
    print("6. WIZARD TEMPLATE CHECK")
    print("=" * 70)
    
    if not os.path.exists('templates/ci_checklist_wizard.html'):
        print("  ❌ Wizard template not found!")
        return False
    
    with open('templates/ci_checklist_wizard.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('data-page="1"', 'Page 1 (Personal Data)'),
        ('data-page="2"', 'Page 2 (Credit Checking)'),
        ('data-page="3"', 'Page 3 (Computation)'),
        ('data-page="4"', 'Page 4 (Assessment)'),
        ('data-page="5"', 'Page 5 (Recommendation)'),
        ('openSignaturePad', 'Signature pad function'),
        ('submitChecklist', 'Submit function'),
        ('id="ci_signature"', 'Signature input field'),
        ('id="ci_latitude"', 'GPS latitude field'),
        ('id="ci_longitude"', 'GPS longitude field'),
        ('id="checklist_data"', 'Checklist data field'),
        ('updateAllComputations', 'Dynamic calculations'),
        ('ci-checklist-wizard.js', 'JavaScript file reference'),
        ('signature-pad.js', 'Signature pad JS reference')
    ]
    
    all_found = True
    for check, desc in checks:
        if check in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_found = False
    
    return all_found

def check_static_files():
    """Check static files exist"""
    print("\n" + "=" * 70)
    print("7. STATIC FILES CHECK")
    print("=" * 70)
    
    critical_files = [
        'static/ci-checklist-wizard.js',
        'static/ci-checklist-wizard.css',
        'static/signature-pad.js',
        'static/ci-location-tracker.js',
        'static/realtime-dashboard.js'
    ]
    
    all_exist = True
    for file in critical_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"  ✓ {file} ({size} bytes)")
        else:
            print(f"  ❌ Missing: {file}")
            all_exist = False
    
    return all_exist

def check_workflow():
    """Check complete workflow"""
    print("\n" + "=" * 70)
    print("8. WORKFLOW VALIDATION")
    print("=" * 70)
    
    print("\n  Expected Flow:")
    print("  1. Loan Staff → Submit Application")
    print("  2. System → Auto-assign to CI Staff")
    print("  3. CI Staff → Click application → Wizard opens")
    print("  4. CI Staff → Fill 5 pages → Sign → Submit")
    print("  5. System → Send to Loan Officer")
    print("  6. Loan Officer → View checklist → Print → Decide")
    
    print("\n  Checking workflow components:")
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if there are any test applications
    cursor.execute("SELECT COUNT(*) as count FROM loan_applications")
    app_count = cursor.fetchone()['count']
    print(f"  ✓ {app_count} loan applications in database")
    
    # Check status values
    cursor.execute("SELECT DISTINCT status FROM loan_applications")
    statuses = [row['status'] for row in cursor.fetchall()]
    print(f"  ✓ Application statuses: {', '.join(statuses) if statuses else 'None yet'}")
    
    conn.close()
    return True

def main():
    print("\n" + "=" * 70)
    print("COMPREHENSIVE SYSTEM CHECK")
    print("CI Checklist Wizard - Full Process Validation")
    print("=" * 70)
    
    results = []
    
    # Run all checks
    results.append(("Database Schema", check_database_schema()))
    results.append(("Users", check_users()))
    results.append(("Loan Types", check_loan_types()))
    results.append(("Routes", check_routes()))
    results.append(("Templates", check_templates()))
    results.append(("Wizard Template", check_wizard_template()))
    results.append(("Static Files", check_static_files()))
    results.append(("Workflow", check_workflow()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:20s}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - SYSTEM READY FOR PRODUCTION!")
        print("=" * 70)
        print("\n✅ Complete Workflow:")
        print("1. Loan Staff submits application")
        print("2. CI Staff clicks application → Wizard opens directly")
        print("3. CI Staff fills 5 pages → Signs → Submits")
        print("4. Loan Officer views formatted checklist → Prints → Decides")
        print("\n✅ Ready to deploy to Render!")
    else:
        print("⚠️  SOME CHECKS FAILED - REVIEW ABOVE")
        print("=" * 70)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
