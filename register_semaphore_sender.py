#!/usr/bin/env python3
"""
Register DCCCO as sender name with Semaphore
"""

import requests

api_key = 'a312c4c24d96b15ef1d997b4d2c6d1d8'

print("="*60)
print("REGISTERING SENDER NAME WITH SEMAPHORE")
print("="*60)

# Try to register sender name
try:
    url = 'https://api.semaphore.co/api/v4/sender-names'
    payload = {
        'apikey': api_key,
        'name': 'DCCCO',
        'type': 'generic'  # or 'brand' depending on Semaphore's requirements
    }
    
    print(f"\nAttempting to register sender name: DCCCO")
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    
    response = requests.post(url, data=payload, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200 or response.status_code == 201:
        print(f"\n✅ Sender name registration submitted!")
        print(f"   It may take a few hours to be approved")
    else:
        print(f"\n⚠ Registration response: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

# Check if there are any existing sender names
print(f"\n{'='*60}")
print(f"CHECKING EXISTING SENDER NAMES")
print(f"{'='*60}")

try:
    url = 'https://api.semaphore.co/api/v4/sender-names'
    params = {'apikey': api_key}
    
    response = requests.get(url, params=params, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        if isinstance(result, list):
            if len(result) == 0:
                print(f"\n⚠ No sender names registered yet")
                print(f"   You need to register one to send SMS")
            else:
                print(f"\n✅ Found {len(result)} sender name(s):")
                for sender in result:
                    print(f"   - {sender}")
        else:
            print(f"\nResponse: {result}")
            
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print(f"\n{'='*60}")
print(f"SOLUTION")
print(f"{'='*60}")
print(f"\nYou need to register a sender name manually:")
print(f"1. Go to https://semaphore.co")
print(f"2. Login to your account")
print(f"3. Go to 'Sender Names' section")
print(f"4. Click 'Add Sender Name'")
print(f"5. Enter: DCCCO")
print(f"6. Submit and wait for approval (usually instant to 24 hours)")
print(f"\nOnce approved, SMS will work with your 1010 credits!")
print(f"\n")
