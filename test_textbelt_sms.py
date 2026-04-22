#!/usr/bin/env python3
"""
TextBelt SMS Test - FREE, works immediately, no registration!
"""

import requests
import sys

# Test phone number
if len(sys.argv) > 1:
    phone = sys.argv[1]
else:
    phone = input("Enter your phone number (e.g., 09751762630): ").strip()

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
print(f"TEXTBELT SMS TEST (FREE - No Registration Needed!)")
print(f"{'='*60}")
print(f"To: {phone}")
print(f"Service: TextBelt (FREE)")
print(f"\nSending...")

try:
    url = 'https://textbelt.com/text'
    payload = {
        'phone': phone,
        'message': 'DCCCO: Your loan application has been APPROVED! This is a test message from the DCCCO system.',
        'key': 'textbelt'  # Free tier key
    }
    
    print(f"\nPayload:")
    print(f"  phone: {phone}")
    print(f"  message: {payload['message']}")
    print(f"  key: textbelt (FREE)")
    
    response = requests.post(url, data=payload, timeout=10)
    
    print(f"\n{'='*60}")
    print(f"RESPONSE")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nParsed JSON: {result}")
        
        if result.get('success'):
            print(f"\n✅ SUCCESS!")
            print(f"   Text ID: {result.get('textId', 'N/A')}")
            print(f"   Quota Remaining Today: {result.get('quotaRemaining', 'N/A')}")
            print(f"\n🎉 SMS SENT! Check your phone in 10-30 seconds!")
            print(f"\n📱 The SMS will come from a US number")
            print(f"   Message will start with 'DCCCO:'")
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n❌ ERROR: {error}")
            
            if 'quota' in error.lower():
                print(f"\n⚠ TextBelt FREE tier allows 1 SMS per day per number")
                print(f"   You've used your free SMS for today")
                print(f"   Options:")
                print(f"   1. Wait until tomorrow")
                print(f"   2. Use a different phone number")
                print(f"   3. Get paid key at https://textbelt.com")
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
print(f"\nTextBelt is FREE and works internationally!")
print(f"No registration, no API key needed!")
print(f"Perfect for testing and demonstrations!")
print(f"\nLimitation: 1 free SMS per day per phone number")
print(f"For production: Get paid key at https://textbelt.com")
print(f"\n")
