#!/usr/bin/env python3
"""
Real SMS Test - Find out why SMS isn't sending
"""

import requests
import sys

# Your API key
api_key = 'a312c4c24d96b15ef1d997b4d2c6d1d8'

# Test phone number (use YOUR phone number)
if len(sys.argv) > 1:
    phone = sys.argv[1]
else:
    phone = input("Enter your phone number (e.g., 09123456789): ").strip()

# Format phone number
if phone.startswith('09') and len(phone) == 11:
    phone = '+63' + phone[1:]
elif phone.startswith('9') and len(phone) == 10:
    phone = '+63' + phone
elif not phone.startswith('+'):
    if phone.startswith('63'):
        phone = '+' + phone
    else:
        phone = '+63' + phone

print(f"\n{'='*60}")
print(f"TESTING SMS SEND")
print(f"{'='*60}")
print(f"To: {phone}")
print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
print(f"\nSending...")

try:
    url = 'https://api.semaphore.co/api/v4/messages'
    
    # TEST 1: Without sendername (should work)
    print(f"\n{'='*60}")
    print(f"TEST 1: WITHOUT SENDERNAME")
    print(f"{'='*60}")
    
    payload = {
        'apikey': api_key,
        'number': phone,
        'message': 'TEST: Your DCCCO loan has been approved! This is a test from the system.'
    }
    
    print(f"\nPayload:")
    print(f"  apikey: {api_key[:10]}...{api_key[-10:]}")
    print(f"  number: {phone}")
    print(f"  message: {payload['message']}")
    print(f"  sendername: (not included)")
    
    response = requests.post(url, data=payload, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"\nParsed JSON: {result}")
            
            # Check if it's an array
            if isinstance(result, list):
                print(f"\n✓ Response is an array with {len(result)} items")
                if len(result) > 0:
                    print(f"  First item: {result[0]}")
                    if 'message_id' in result[0]:
                        print(f"\n✅ SUCCESS! Message ID: {result[0]['message_id']}")
                        print(f"   Status: {result[0].get('status', 'N/A')}")
                        print(f"\n🎉 SMS SENT! Check your phone in 10-30 seconds!")
                        print(f"\n💰 Your credits should decrease from 1010")
                    else:
                        print(f"\n❌ ERROR: No message_id in response")
                        if 'error' in result[0] or 'errors' in result[0]:
                            print(f"   Error: {result[0]}")
            elif isinstance(result, dict):
                print(f"\n✓ Response is a dictionary")
                if 'message_id' in result:
                    print(f"\n✅ SUCCESS! Message ID: {result['message_id']}")
                    print(f"\n🎉 SMS SENT! Check your phone in 10-30 seconds!")
                elif 'error' in result or 'errors' in result or 'sendername' in result or 'number' in result:
                    print(f"\n❌ ERROR in response:")
                    print(f"   {result}")
                    if 'sendername' in result:
                        print(f"\n   ⚠ Sendername error - this is expected, we're not using sendername")
                    if 'number' in result:
                        print(f"\n   ⚠ Number format error - check phone number: {phone}")
                else:
                    print(f"\n⚠ Unexpected response format:")
                    print(f"   {result}")
        except ValueError as e:
            print(f"\n⚠ Response is not JSON: {response.text}")
    else:
        print(f"\n❌ HTTP ERROR: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {str(e)}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*60}")
print(f"TEST COMPLETE")
print(f"{'='*60}")
print(f"\nIf you see 'SUCCESS' above, check your phone!")
print(f"If you see 'ERROR', read the error message carefully.")
print(f"\nCommon issues:")
print(f"  - 'number format invalid': Phone number format is wrong")
print(f"  - 'sendername invalid': Sendername not registered (we removed this)")
print(f"\n")

