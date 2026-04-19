#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify Google Cloud Vision OCR setup
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Testing Google Cloud Vision OCR Setup")
print("=" * 60)

# Test 1: Check if credentials file exists
print("\n1. Checking credentials file...")
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
if os.path.exists(creds_path):
    print(f"   ✓ Credentials file found: {creds_path}")
else:
    print(f"   ✗ Credentials file NOT found: {creds_path}")
    print("   Please ensure the JSON file is in the project root")
    exit(1)

# Test 2: Check if google-cloud-vision is installed
print("\n2. Checking google-cloud-vision package...")
try:
    import google.cloud.vision
    print("   ✓ google-cloud-vision package installed")
except ImportError:
    print("   ✗ google-cloud-vision NOT installed")
    print("   Run: python -m pip install google-cloud-vision")
    exit(1)

# Test 3: Try to initialize Vision client
print("\n3. Initializing Google Cloud Vision client...")
try:
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()
    print("   ✓ Vision client initialized successfully")
except Exception as e:
    print(f"   ✗ Failed to initialize client: {str(e)}")
    print("\n   Troubleshooting:")
    print("   - Check if JSON file is valid")
    print("   - Verify Cloud Vision API is enabled in Google Cloud Console")
    print("   - Ensure service account has proper permissions")
    exit(1)

# Test 4: Test OCR service module
print("\n4. Testing OCR service module...")
try:
    from ocr_service import get_ocr_service
    ocr_service = get_ocr_service()
    print("   ✓ OCR service module loaded successfully")
except Exception as e:
    print(f"   ✗ Failed to load OCR service: {str(e)}")
    exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nYour OCR setup is complete and ready to use!")
print("\nNext steps:")
print("1. Start your Flask app: python app.py")
print("2. Login as LPS (loan_staff)")
print("3. Go to 'Submit New Application'")
print("4. Upload images of filled forms")
print("5. Click 'Extract Data from Images (AI)' button")
print("\nThe system will automatically extract and fill form fields!")
print("=" * 60)
