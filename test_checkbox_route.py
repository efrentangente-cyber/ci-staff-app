#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the checkbox summary route locally
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_route():
    """Test if the route is accessible"""
    try:
        print("Importing app...")
        import app as flask_app
        
        print("Creating test client...")
        client = flask_app.app.test_client()
        
        print("Testing route /ci/checklist/summary/1...")
        response = client.get('/ci/checklist/summary/1', follow_redirects=False)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 302:
            print(f"Redirect to: {response.location}")
            print("✅ Route exists (redirecting to login as expected)")
            return True
        elif response.status_code == 200:
            print("✅ Route accessible")
            return True
        elif response.status_code == 500:
            print("❌ Internal Server Error")
            print(f"Response: {response.data[:500]}")
            return False
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing CI Checkbox Summary Route")
    print("=" * 60)
    
    if test_route():
        print("\n✅ Route test passed!")
    else:
        print("\n❌ Route test failed!")
