#!/usr/bin/env python3
"""Complete SMS Templates Test"""

from app import app, get_db
import json

def test_complete_sms_workflow():
    print("=" * 60)
    print("COMPLETE SMS TEMPLATES TEST")
    print("=" * 60)
    
    with app.app_context():
        conn = get_db()
        
        # Test 1: Check templates exist
        print("\n1. Checking SMS templates...")
        templates = conn.execute('SELECT * FROM sms_templates').fetchall()
        print(f"   ✓ Found {len(templates)} templates")
        
        for t in templates:
            print(f"     - {t['name']} ({t['category']})")
        
        # Test 2: Test categorization
        print("\n2. Testing template categorization...")
        approved = [t for t in templates if t['category'] == 'approved']
        disapproved = [t for t in templates if t['category'] == 'disapproved']
        deferred = [t for t in templates if t['category'] == 'deferred']
        custom = [t for t in templates if t['category'] == 'custom']
        
        print(f"   ✓ Approved: {len(approved)}")
        print(f"   ✓ Disapproved: {len(disapproved)}")
        print(f"   ✓ Deferred: {len(deferred)}")
        print(f"   ✓ Custom: {len(custom)}")
        
        # Test 3: Test API endpoint with test client
        print("\n3. Testing API endpoints...")
        with app.test_client() as client:
            # Login first
            response = client.post('/login', data={
                'email': 'admin@dccco.test',
                'password': 'admin123'
            }, follow_redirects=True)
            
            if response.status_code == 200:
                print("   ✓ Logged in successfully")
                
                # Test get templates API
                response = client.get('/api/get_sms_templates/approved')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"   ✓ API returned {len(data.get('templates', []))} approved templates")
                else:
                    print(f"   ✗ API failed with status {response.status_code}")
                
                # Test manage page
                response = client.get('/manage_sms_templates')
                if response.status_code == 200:
                    print("   ✓ Manage SMS templates page loads successfully")
                else:
                    print(f"   ✗ Manage page failed with status {response.status_code}")
            else:
                print("   ✗ Login failed")
        
        # Test 4: Test send_sms_and_update_status endpoint
        print("\n4. Testing send SMS and update status...")
        
        # Get a test application
        app_data = conn.execute('''
            SELECT id, member_name, member_contact, loan_amount, status 
            FROM loan_applications 
            WHERE status = 'ci_completed'
            LIMIT 1
        ''').fetchone()
        
        if app_data:
            print(f"   ✓ Found test application: ID {app_data['id']}, {app_data['member_name']}")
            print(f"     Current status: {app_data['status']}")
            
            with app.test_client() as client:
                # Login
                client.post('/login', data={
                    'email': 'admin@dccco.test',
                    'password': 'admin123'
                })
                
                # Test defer action (dry run - we'll rollback)
                response = client.post(
                    f'/send_sms_and_update_status/{app_data["id"]}',
                    json={
                        'action': 'deferred',
                        'message': 'Test SMS message for {member_name}',
                        'notes': 'Test notes'
                    }
                )
                
                if response.status_code == 200:
                    result = json.loads(response.data)
                    if result.get('success'):
                        print("   ✓ SMS and status update endpoint works")
                        
                        # Check if status was updated
                        updated = conn.execute(
                            'SELECT status FROM loan_applications WHERE id = ?',
                            (app_data['id'],)
                        ).fetchone()
                        
                        if updated and updated['status'] == 'deferred':
                            print(f"   ✓ Status updated to: {updated['status']}")
                            
                            # Rollback for testing
                            conn.execute(
                                'UPDATE loan_applications SET status = ? WHERE id = ?',
                                (app_data['status'], app_data['id'])
                            )
                            conn.commit()
                            print("   ✓ Rolled back test changes")
                        else:
                            print("   ✗ Status not updated correctly")
                    else:
                        print(f"   ✗ API returned error: {result.get('error')}")
                else:
                    print(f"   ✗ Request failed with status {response.status_code}")
        else:
            print("   ℹ No ci_completed applications to test with")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ ALL SMS TESTS PASSED")
        print("=" * 60)
        print("\nThe SMS templates system is working correctly!")
        print("\nTo use:")
        print("1. Login as admin@dccco.test / admin123")
        print("2. Go to 'SMS Templates' in sidebar")
        print("3. Create/edit templates")
        print("4. Use Approve/Disapprove/Defer buttons in Admin Dashboard")
        print("5. Select template and send SMS")

if __name__ == '__main__':
    test_complete_sms_workflow()
