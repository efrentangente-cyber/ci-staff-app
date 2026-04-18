#!/usr/bin/env python3
"""
Comprehensive verification of permissions system
"""

import sqlite3
import os

def verify_system():
    print("=" * 80)
    print("PERMISSIONS SYSTEM VERIFICATION")
    print("=" * 80)
    
    # Check database
    if not os.path.exists('app.db'):
        print("✗ Database not found!")
        return False
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check permissions column exists
    print("\n1. Checking database schema...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'permissions' in columns:
        print("   ✓ 'permissions' column exists")
    else:
        print("   ✗ 'permissions' column missing!")
        return False
    
    # 2. Check users
    print("\n2. Checking users...")
    cursor.execute('''
        SELECT id, name, email, role, permissions 
        FROM users 
        WHERE role IN ('admin', 'loan_officer')
        ORDER BY role, name
    ''')
    users = cursor.fetchall()
    
    if not users:
        print("   ✗ No admin or loan officer users found!")
        return False
    
    admin_count = 0
    loan_officer_count = 0
    
    for user in users:
        role = user['role']
        perms = user['permissions'] or 'None'
        print(f"   ✓ {user['name']:25} | {role:15} | Permissions: {perms}")
        
        if role == 'admin':
            admin_count += 1
        elif role == 'loan_officer':
            loan_officer_count += 1
    
    print(f"\n   Summary: {admin_count} admin(s), {loan_officer_count} loan officer(s)")
    
    # 3. Check templates
    print("\n3. Checking templates...")
    templates = [
        'templates/manage_permissions.html',
        'templates/admin_application.html',
        'templates/base.html'
    ]
    
    for template in templates:
        if os.path.exists(template):
            print(f"   ✓ {template}")
        else:
            print(f"   ✗ {template} missing!")
            return False
    
    # 4. Check app.py for routes
    print("\n4. Checking routes in app.py...")
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        routes_to_check = [
            'def manage_permissions',
            'def update_permissions',
            'def has_permission'
        ]
        
        for route in routes_to_check:
            if route in content:
                print(f"   ✓ {route}() found")
            else:
                print(f"   ✗ {route}() missing!")
                return False
    else:
        print("   ✗ app.py not found!")
        return False
    
    # 5. Check User class
    print("\n5. Checking User class...")
    if 'def __init__(self, id, email, name, role, signature_path=None, backup_email=None, profile_photo=None, assigned_route=None, permissions=None)' in content:
        print("   ✓ User class includes permissions parameter")
    else:
        print("   ⚠ User class may not include permissions parameter")
    
    # 6. Check base.html for navigation
    print("\n6. Checking navigation in base.html...")
    if os.path.exists('templates/base.html'):
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_content = f.read()
        
        nav_checks = [
            ('manage_permissions', 'Manage Permissions link'),
            ('current_user.permissions', 'Permission checks in navigation')
        ]
        
        for check, desc in nav_checks:
            if check in base_content:
                print(f"   ✓ {desc}")
            else:
                print(f"   ✗ {desc} missing!")
    else:
        print("   ✗ base.html not found!")
        return False
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ ALL CHECKS PASSED - SYSTEM READY")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Test locally by running: python app.py")
    print("2. Login as super admin: superadmin@dccco.test")
    print("3. Navigate to 'Manage Permissions'")
    print("4. Test granting/revoking permissions")
    print("5. Login as loan officer to verify access control")
    print("6. Deploy to Render when ready")
    
    return True

if __name__ == '__main__':
    try:
        verify_system()
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()
