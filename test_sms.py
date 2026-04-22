#!/usr/bin/env python3
"""
SMS API Test Script
Tests the Semaphore SMS API with your credentials
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_semaphore_sms():
    """Test Semaphore SMS API"""
    api_key = os.getenv('SEMAPHORE_API_KEY', '')
    
    if not api_key:
        print("[ERROR] SEMAPHORE_API_KEY not found in .env file")
        return False
    
    print("=" * 60)
    print("SEMAPHORE SMS API TEST")
    print("=" * 60)
    print(f"\nAPI Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"Credits: Checking...")
    
    # Check account balance
    try:
        balance_url = 'https://api.semaphore.co/api/v4/account'
        params = {'apikey': api_key}
        response = requests.get(balance_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCCESS] API Key is valid!")
            print(f"Account Name: {data.get('account_name', 'N/A')}")
            print(f"Credits: {data.get('credit_balance', 'N/A')}")
            print(f"Status: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"\n[ERROR] API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Failed to check balance: {str(e)}")
        return False

def send_test_sms(phone_number, message="Test message from DCCCO CI Staff Application"):
    """Send a test SMS"""
    api_key = os.getenv('SEMAPHORE_API_KEY', '')
    
    if not api_key:
        print("[ERROR] SEMAPHORE_API_KEY not found")
        return False
    
    print("\n" + "=" * 60)
    print("SENDING TEST SMS")
    print("=" * 60)
    
    # Format phone number
    phone = phone_number.strip()
    if not phone.startswith('+'):
        if phone.startswith('0'):
            phone = '+63' + phone[1:]  # Philippine number
        elif not phone.startswith('63'):
            phone = '+63' + phone
        else:
            phone = '+' + phone
    
    print(f"\nTo: {phone}")
    print(f"Message: {message}")
    print(f"\nSending...")
    
    try:
        url = 'https://api.semaphore.co/api/v4/messages'
        payload = {
            'apikey': api_key,
            'number': phone,
            'message': message,
            'sendername': 'DCCCO'
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n[SUCCESS] SMS sent successfully!")
            print(f"Message ID: {result.get('message_id', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
            return True
        else:
            print(f"\n[ERROR] Failed to send SMS: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {str(e)}")
        return False

def main():
    """Main test function"""
    print("\n")
    
    # Test 1: Check API key and balance
    if not test_semaphore_sms():
        print("\n[FAILED] API key test failed. Please check your SEMAPHORE_API_KEY in .env")
        return
    
    # Test 2: Send test SMS (optional)
    print("\n" + "=" * 60)
    print("SMS TESTING OPTIONS")
    print("=" * 60)
    print("1. Send single SMS")
    print("2. Send bulk SMS (multiple numbers)")
    print("3. Skip testing")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == '1':
        phone = input("Enter phone number (e.g., 09123456789): ").strip()
        if phone:
            send_test_sms(phone)
        else:
            print("[SKIPPED] No phone number provided")
    
    elif choice == '2':
        print("\nEnter phone numbers separated by commas")
        print("Example: 09123456789, 09987654321, 09111222333")
        phones = input("Phone numbers: ").strip()
        
        if phones:
            phone_list = [p.strip() for p in phones.split(',') if p.strip()]
            print(f"\nWill send to {len(phone_list)} numbers:")
            for i, p in enumerate(phone_list, 1):
                print(f"  {i}. {p}")
            
            confirm = input("\nProceed? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                message = "Test bulk SMS from DCCCO CI Staff Application"
                success_count = 0
                
                for phone in phone_list:
                    if send_test_sms(phone, message):
                        success_count += 1
                
                print(f"\n{'='*60}")
                print(f"BULK SMS COMPLETE")
                print(f"Success: {success_count}/{len(phone_list)}")
                print(f"{'='*60}")
            else:
                print("[CANCELLED] Bulk SMS cancelled")
        else:
            print("[SKIPPED] No phone numbers provided")
    
    else:
        print("[SKIPPED] Test SMS not sent")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nYour SMS API is configured and ready to use!")
    print("The system will automatically send SMS notifications for:")
    print("  - Loan application status updates")
    print("  - CI assignment notifications")
    print("  - Important system alerts")
    print("\nNEW: Bulk SMS Feature Available!")
    print("  - Send same message to multiple numbers")
    print("  - Use comma-separated phone numbers")
    print("  - Example: 09123456789, 09987654321")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
