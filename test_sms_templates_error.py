#!/usr/bin/env python3
"""Test SMS templates to find the error"""

import sys
import traceback
from app import app, get_db

def test_sms_templates():
    print("=" * 60)
    print("TESTING SMS TEMPLATES")
    print("=" * 60)
    
    try:
        # Test 1: Check if sms_templates table exists
        print("\n1. Checking sms_templates table...")
        conn = get_db()
        cursor = conn.cursor()
        
        result = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sms_templates'"
        ).fetchone()
        
        if result:
            print("   ✓ sms_templates table exists")
        else:
            print("   ✗ sms_templates table NOT found")
            print("   → Run: python migrate_add_sms_templates.py")
            return False
        
        # Test 2: Check table structure
        print("\n2. Checking table structure...")
        schema = cursor.execute("PRAGMA table_info(sms_templates)").fetchall()
        print("   Columns:")
        for col in schema:
            print(f"     - {col[1]} ({col[2]})")
        
        # Test 3: Try to query templates
        print("\n3. Querying templates...")
        templates = cursor.execute("SELECT * FROM sms_templates").fetchall()
        print(f"   ✓ Found {len(templates)} templates")
        
        for t in templates:
            print(f"     - ID: {t[0]}, Name: {t[1]}, Category: {t[2]}")
        
        # Test 4: Test the route with app context
        print("\n4. Testing manage_sms_templates route...")
        with app.test_client() as client:
            # Try to access without login (should redirect)
            response = client.get('/manage_sms_templates')
            print(f"   Response status (no auth): {response.status_code}")
            
            if response.status_code == 302:
                print("   ✓ Route exists and requires authentication")
            elif response.status_code == 404:
                print("   ✗ Route not found (404)")
                return False
            elif response.status_code == 500:
                print("   ✗ Internal server error (500)")
                print("   → Check app.py for errors in manage_sms_templates route")
                return False
        
        # Test 5: Test API route
        print("\n5. Testing API route...")
        with app.test_client() as client:
            response = client.get('/api/get_sms_templates/approved')
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 302:
                print("   ✓ API route exists and requires authentication")
            elif response.status_code == 404:
                print("   ✗ API route not found")
                return False
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ SMS TEMPLATES SYSTEM OK")
        print("=" * 60)
        print("\nIf you're getting an error:")
        print("1. Check browser console for JavaScript errors")
        print("2. Check Flask terminal for Python errors")
        print("3. Make sure you're logged in as admin or loan_officer")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_sms_templates()
    sys.exit(0 if success else 1)
