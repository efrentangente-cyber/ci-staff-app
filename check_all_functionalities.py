import sqlite3
import os
from datetime import datetime

def check_database():
    """Check database structure and data"""
    print("=" * 60)
    print("DATABASE FUNCTIONALITY CHECK")
    print("=" * 60)
    
    if not os.path.exists('app.db'):
        print("❌ Database file not found!")
        return False
    
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables
    print("\n1. CHECKING DATABASE TABLES:")
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    expected_tables = ['users', 'loan_applications', 'documents', 'messages', 
                      'notifications', 'direct_messages', 'location_tracking', 
                      'loan_types', 'system_settings']
    
    existing_tables = [t['name'] for t in tables]
    for table in expected_tables:
        if table in existing_tables:
            print(f"   ✓ {table}")
        else:
            print(f"   ❌ {table} - MISSING")
    
    # Check users
    print("\n2. CHECKING USERS:")
    users = cursor.execute('SELECT id, email, name, role, is_approved FROM users').fetchall()
    if users:
        for user in users:
            approval = "✓ Approved" if user['is_approved'] else "⚠ Pending"
            print(f"   {user['id']}. {user['name']} ({user['email']})")
            print(f"      Role: {user['role']} | Status: {approval}")
    else:
        print("   ⚠ No users found")
    
    # Check loan types
    print("\n3. CHECKING LOAN TYPES:")
    loan_types = cursor.execute('SELECT id, name, is_active FROM loan_types').fetchall()
    if loan_types:
        active_count = sum(1 for lt in loan_types if lt['is_active'])
        print(f"   Total: {len(loan_types)} | Active: {active_count}")
        for lt in loan_types[:5]:  # Show first 5
            status = "✓ Active" if lt['is_active'] else "✗ Inactive"
            print(f"   - {lt['name']} ({status})")
        if len(loan_types) > 5:
            print(f"   ... and {len(loan_types) - 5} more")
    else:
        print("   ⚠ No loan types found")
    
    # Check system settings
    print("\n4. CHECKING SYSTEM SETTINGS:")
    settings = cursor.execute('SELECT setting_key, setting_value FROM system_settings').fetchall()
    if settings:
        for setting in settings:
            print(f"   - {setting['setting_key']}: {setting['setting_value']}")
    else:
        print("   ⚠ No system settings found")
    
    # Check loan applications
    print("\n5. CHECKING LOAN APPLICATIONS:")
    apps = cursor.execute('SELECT COUNT(*) as count FROM loan_applications').fetchone()
    print(f"   Total Applications: {apps['count']}")
    
    if apps['count'] > 0:
        status_counts = cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM loan_applications 
            GROUP BY status
        ''').fetchall()
        for sc in status_counts:
            print(f"   - {sc['status']}: {sc['count']}")
    
    # Check notifications
    print("\n6. CHECKING NOTIFICATIONS:")
    notif = cursor.execute('SELECT COUNT(*) as count FROM notifications').fetchone()
    unread = cursor.execute('SELECT COUNT(*) as count FROM notifications WHERE is_read=0').fetchone()
    print(f"   Total: {notif['count']} | Unread: {unread['count']}")
    
    # Check messages
    print("\n7. CHECKING MESSAGES:")
    msgs = cursor.execute('SELECT COUNT(*) as count FROM messages').fetchone()
    direct_msgs = cursor.execute('SELECT COUNT(*) as count FROM direct_messages').fetchone()
    print(f"   Application Messages: {msgs['count']}")
    print(f"   Direct Messages: {direct_msgs['count']}")
    
    conn.close()
    return True

def check_files():
    """Check required files and folders"""
    print("\n" + "=" * 60)
    print("FILE SYSTEM CHECK")
    print("=" * 60)
    
    # Check required folders
    print("\n1. CHECKING FOLDERS:")
    folders = ['uploads', 'signatures', 'message_attachments', 'voice_messages', 'templates', 'static']
    for folder in folders:
        if os.path.exists(folder):
            count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
            print(f"   ✓ {folder}/ ({count} files)")
        else:
            print(f"   ❌ {folder}/ - MISSING")
    
    # Check key template files
    print("\n2. CHECKING TEMPLATES:")
    templates = [
        'login.html', 'signup.html', 'base.html',
        'admin_dashboard.html', 'loan_dashboard.html', 'ci_dashboard.html',
        'submit_application.html', 'ci_application.html', 'admin_application.html',
        'manage_users.html', 'manage_loan_types.html', 'system_settings.html',
        'reports.html', 'messages_dark.html', 'notifications.html'
    ]
    for template in templates:
        path = os.path.join('templates', template)
        if os.path.exists(path):
            print(f"   ✓ {template}")
        else:
            print(f"   ❌ {template} - MISSING")
    
    # Check key static files
    print("\n3. CHECKING STATIC FILES:")
    static_files = [
        'signature-pad.js', 'ci-location-tracker.js', 'realtime-dashboard.js',
        'datatable.js', 'route_mapping.js', 'voice-recorder.js', 'video-call.js'
    ]
    for sfile in static_files:
        path = os.path.join('static', sfile)
        if os.path.exists(path):
            print(f"   ✓ {sfile}")
        else:
            print(f"   ❌ {sfile} - MISSING")

def check_routes():
    """Check if main routes are defined in app.py"""
    print("\n" + "=" * 60)
    print("ROUTE FUNCTIONALITY CHECK")
    print("=" * 60)
    
    if not os.path.exists('app.py'):
        print("❌ app.py not found!")
        return False
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n1. CHECKING CORE ROUTES:")
    routes = [
        ('/login', 'Login'),
        ('/signup', 'User Registration'),
        ('/logout', 'Logout'),
        ('/loan_dashboard', 'Loan Staff Dashboard'),
        ('/ci_dashboard', 'CI Staff Dashboard'),
        ('/admin_dashboard', 'Admin Dashboard'),
        ('/submit_application', 'Submit Application'),
        ('/ci_application/<id>', 'CI Application View'),
        ('/admin_application/<id>', 'Admin Application View'),
        ('/manage_users', 'Manage Users'),
        ('/manage_loan_types', 'Manage Loan Types'),
        ('/system_settings', 'System Settings'),
        ('/reports', 'Reports'),
        ('/messages', 'Messages'),
        ('/notifications', 'Notifications'),
        ('/ci_tracking', 'CI Tracking'),
    ]
    
    for route, name in routes:
        route_pattern = f"@app.route('{route}"
        if route_pattern in content:
            print(f"   ✓ {name} ({route})")
        else:
            print(f"   ❌ {name} ({route}) - NOT FOUND")
    
    print("\n2. CHECKING API ENDPOINTS:")
    api_routes = [
        ('/api/user_info', 'User Info API'),
        ('/api/ci_applications', 'CI Applications API'),
        ('/get_loan_types', 'Get Loan Types'),
        ('/add_loan_type', 'Add Loan Type'),
        ('/update_location', 'Update Location'),
        ('/send_direct_message', 'Send Direct Message'),
    ]
    
    for route, name in api_routes:
        route_pattern = f"@app.route('{route}"
        if route_pattern in content:
            print(f"   ✓ {name} ({route})")
        else:
            print(f"   ❌ {name} ({route}) - NOT FOUND")
    
    print("\n3. CHECKING SOCKETIO EVENTS:")
    socketio_events = [
        ('connect', 'Socket Connect'),
        ('disconnect', 'Socket Disconnect'),
        ('join_application', 'Join Application Room'),
        ('join_tracking', 'Join Tracking Room'),
    ]
    
    for event, name in socketio_events:
        event_pattern = f"@socketio.on('{event}')"
        if event_pattern in content:
            print(f"   ✓ {name}")
        else:
            print(f"   ❌ {name} - NOT FOUND")

def check_features():
    """Check specific features implementation"""
    print("\n" + "=" * 60)
    print("FEATURE IMPLEMENTATION CHECK")
    print("=" * 60)
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    features = [
        ('setup_production_users', 'Production User Setup'),
        ('validate_password_strength', 'Password Validation'),
        ('create_notification', 'Notification System'),
        ('send_verification_email', 'Email Verification'),
        ('generate_report', 'Report Generation'),
        ('update_ci_route', 'Route Assignment'),
        ('update_system_settings', 'System Settings Update'),
        ('forgot_password', 'Password Reset'),
        ('send_direct_message', 'Direct Messaging'),
        ('update_location', 'Location Tracking'),
    ]
    
    print("\n1. CHECKING KEY FEATURES:")
    for func, name in features:
        if f"def {func}" in content:
            print(f"   ✓ {name}")
        else:
            print(f"   ❌ {name} - NOT FOUND")
    
    print("\n2. CHECKING SECURITY FEATURES:")
    security = [
        ('login_required', 'Login Required Decorator'),
        ('require_admin', 'Admin Authorization'),
        ('require_admin_or_loan_officer', 'Loan Officer Authorization'),
        ('add_security_headers', 'Security Headers'),
        ('generate_password_hash', 'Password Hashing'),
    ]
    
    for feature, name in security:
        if feature in content:
            print(f"   ✓ {name}")
        else:
            print(f"   ❌ {name} - NOT FOUND")

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "CI STAFF SYSTEM - FUNCTIONALITY CHECK" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        check_database()
        check_files()
        check_routes()
        check_features()
        
        print("\n" + "=" * 60)
        print("CHECK COMPLETE")
        print("=" * 60)
        print("\n✓ All functionality checks completed successfully!")
        print("\nNOTE: This script checks for the presence of features.")
        print("      Run the application to test actual functionality.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR during check: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
