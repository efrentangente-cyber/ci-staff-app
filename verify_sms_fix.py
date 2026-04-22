#!/usr/bin/env python3
"""
Quick SMS Verification Script
Tests if SMS is actually being sent with your Semaphore API
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def verify_sms_api():
    """Verify SMS API is working"""
    api_key = os.getenv('SEMAPHORE_API_KEY', '')
    
    if not api_key:
        print("❌ ERROR: No SEMAPHORE_API_KEY found in .env")
        return False
    
    print("=" * 60)
    print("SMS API VERIFICATION")
    print("=" * 60)
    
    # Step 1: Check account status
    print("\n[1/3] Checking account status...")
    try:
        url = 'https://api.semaphore.co/api/v4/account'
        params = {'apikey': api_key}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Account: {data.get('account_name', 'N/A')}")
            print(f"✓ Credits: {data.get('credit_balance', 'N/A')}")
            print(f"✓ Status: {data.get('status', 'N/A')}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    # Step 2: Test phone number format
    print("\n[2/3] Testing phone number formatting...")
    test_numbers = [
        "09123456789",
        "9123456789",
        "+639123456789",
        "639123456789"
    ]
    
    for num in test_numbers:
        # Clean and format
        phone = num.strip()
        if not phone.startswith('+'):
            if phone.startswith('0'):
                phone = '+63' + phone[1:]
            elif not phone.startswith('63'):
                phone = '+63' + phone
            else:
                phone = '+' + phone
        print(f"  {num:20s} → {phone}")
    
    # Step 3: Ask if user wants to send test SMS
    print("\n[3/3] Send test SMS?")
    print("=" * 60)
    
    choice = input("Enter phone number to test (or press Enter to skip): ").strip()
    
    if not choice:
        print("\n✓ Verification complete (test SMS skipped)")
        return True
    
    # Format phone number
    phone = choice
    if not phone.startswith('+'):
        if phone.startswith('0'):
            phone = '+63' + phone[1:]
        elif not phone.startswith('63'):
            phone = '+63' + phone
        else:
            phone = '+' + phone
    
    print(f"\nSending test SMS to {phone}...")
    
    try:
        url = 'https://api.semaphore.co/api/v4/messages'
        payload = {
            'apikey': api_key,
            'number': phone,
            'message': 'Test SMS from DCCCO CI Staff Application - SMS is working!',
            'sendername': 'DCCCO'
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("\n✓ SMS SENT SUCCESSFULLY!")
                print(f"  Response: {result}")
                
                # Check if it's an array or object
                if isinstance(result, list) and len(result) > 0:
                    msg_data = result[0]
                    print(f"  Message ID: {msg_data.get('message_id', 'N/A')}")
                    print(f"  Status: {msg_data.get('status', 'N/A')}")
                elif isinstance(result, dict):
                    print(f"  Message ID: {result.get('message_id', 'N/A')}")
                    print(f"  Status: {result.get('status', 'N/A')}")
                
                return True
            except ValueError:
                # Not JSON, but 200 OK
                if 'success' in response.text.lower() or 'sent' in response.text.lower():
                    print("\n✓ SMS SENT SUCCESSFULLY!")
                    return True
                else:
                    print("\n⚠ Unexpected response format")
                    return False
        else:
            print(f"\n❌ Failed to send SMS")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending SMS: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n")
    success = verify_sms_api()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ SMS API IS WORKING!")
        print("=" * 60)
        print("\nYour SMS functionality should now work in the application.")
        print("The system will send SMS for:")
        print("  • Loan approvals")
        print("  • Loan rejections")
        print("  • Loan deferrals")
    else:
        print("❌ SMS API VERIFICATION FAILED")
        print("=" * 60)
        print("\nPlease check:")
        print("  1. SEMAPHORE_API_KEY in .env file")
        print("  2. Internet connection")
        print("  3. API key is valid and active")
        print("  4. Account has sufficient credits")
    
    print("\n")
