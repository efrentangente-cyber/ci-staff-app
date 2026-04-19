# Google Cloud Vision API Setup Guide

## Overview
This guide will help you set up Google Cloud Vision API for OCR (Optical Character Recognition) functionality in your loan application system.

---

## Step 1: Create Google Cloud Account

1. Go to https://console.cloud.google.com
2. Sign in with your Google account (or create one)
3. Accept terms of service
4. You get **$300 free credit** for 90 days!

---

## Step 2: Create a New Project

1. Click on project dropdown (top left, next to "Google Cloud")
2. Click "NEW PROJECT"
3. Enter project details:
   - **Project name**: `ci-loan-ocr` (or any name you prefer)
   - **Organization**: Leave as default
4. Click "CREATE"
5. Wait for project to be created (takes ~30 seconds)
6. Select your new project from the dropdown

---

## Step 3: Enable Cloud Vision API

1. In the search bar at top, type: **"Cloud Vision API"**
2. Click on "Cloud Vision API" result
3. Click the blue **"ENABLE"** button
4. Wait for API to be enabled (~1 minute)
5. You'll see "API enabled" message

---

## Step 4: Create Service Account

1. In left sidebar, click **"Credentials"** (or search for it)
2. Click **"+ CREATE CREDENTIALS"** at top
3. Select **"Service account"**
4. Fill in details:
   - **Service account name**: `ci-ocr-service`
   - **Service account ID**: (auto-filled)
   - **Description**: "OCR service for loan applications"
5. Click **"CREATE AND CONTINUE"**
6. Grant role:
   - Click "Select a role" dropdown
   - Search for: **"Cloud Vision AI Service Agent"**
   - Select it
7. Click **"CONTINUE"**
8. Click **"DONE"** (skip optional steps)

---

## Step 5: Create and Download Key

1. You'll see your service account in the list
2. Click on the service account email (e.g., `ci-ocr-service@...`)
3. Go to **"KEYS"** tab
4. Click **"ADD KEY"** → **"Create new key"**
5. Select **"JSON"** format
6. Click **"CREATE"**
7. A JSON file will download automatically
   - **IMPORTANT**: Keep this file safe and secure!
   - File name example: `ci-loan-ocr-abc123def456.json`

---

## Step 6: Configure Your Application

### For Local Development:

1. **Save the JSON key file**:
   - Put it in your project root folder
   - Example: `C:\xampp2\htdocs\geo_smart_ci\google-credentials.json`

2. **Add to .env file**:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   ```

3. **Add to .gitignore** (IMPORTANT - don't commit credentials!):
   ```
   google-credentials.json
   *.json
   ```

### For Render Deployment:

1. **Go to Render Dashboard**:
   - https://dashboard.render.com
   - Select your service

2. **Add Environment Variable**:
   - Go to "Environment" tab
   - Click "Add Environment Variable"
   - **Key**: `GOOGLE_APPLICATION_CREDENTIALS`
   - **Value**: Paste the ENTIRE contents of your JSON file
   - Click "Save Changes"

3. **Alternative Method** (if above doesn't work):
   - Create a secret file in Render
   - Go to "Secret Files" section
   - Filename: `google-credentials.json`
   - Contents: Paste your JSON file contents
   - Then set env var: `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/google-credentials.json`

---

## Step 7: Install Dependencies

Run this command in your project directory:

```bash
pip install google-cloud-vision Pillow
```

Or if using requirements.txt (already updated):

```bash
pip install -r requirements.txt
```

---

## Step 8: Test the Setup

### Test 1: Check if API is configured

1. Start your Flask app
2. Login as LPS (loan_staff)
3. Open browser console (F12)
4. Run this in console:
   ```javascript
   fetch('/api/ocr/test')
     .then(r => r.json())
     .then(d => console.log(d))
   ```
5. Should see: `{success: true, message: "OCR service is configured and ready"}`

### Test 2: Upload and Extract

1. Go to "Submit New Application"
2. Upload an image of a filled DCCCO form
3. Click "Extract Data from Images (AI)" button
4. Wait for processing (5-10 seconds)
5. Form fields should auto-fill!

---

## Pricing & Free Tier

### Free Tier (Monthly):
- **First 1,000 images**: FREE
- **Text detection**: FREE for first 1,000 units

### After Free Tier:
- **1,001 - 5,000,000 images**: $1.50 per 1,000 images
- **Example**: 100 applications/month = FREE
- **Example**: 5,000 applications/month = $6/month

### Cost Calculator:
- 10 apps/day × 30 days = 300 images/month = **FREE**
- 50 apps/day × 30 days = 1,500 images/month = **$0.75/month**
- 100 apps/day × 30 days = 3,000 images/month = **$3/month**

**Conclusion**: Very affordable for most use cases!

---

## Troubleshooting

### Error: "Could not load credentials"

**Solution**:
1. Check if JSON file exists in correct location
2. Verify .env file has correct path
3. Restart Flask app after adding credentials

### Error: "API not enabled"

**Solution**:
1. Go to Google Cloud Console
2. Search "Cloud Vision API"
3. Click "ENABLE"
4. Wait 1-2 minutes

### Error: "Permission denied"

**Solution**:
1. Check service account has "Cloud Vision AI Service Agent" role
2. Regenerate key if needed
3. Make sure JSON file is not corrupted

### Error: "Quota exceeded"

**Solution**:
1. You've used more than 1,000 images this month
2. Either wait for next month (quota resets)
3. Or enable billing to continue (costs apply)

### OCR not extracting data correctly

**Solution**:
1. Ensure images are clear and high resolution
2. Make sure text is not too small
3. Avoid blurry or dark images
4. Try uploading multiple images of same form

---

## Security Best Practices

### DO:
✅ Keep JSON key file secure
✅ Add to .gitignore
✅ Use environment variables
✅ Rotate keys periodically (every 90 days)
✅ Limit service account permissions

### DON'T:
❌ Commit credentials to Git
❌ Share JSON file publicly
❌ Hardcode credentials in code
❌ Use same key for multiple projects
❌ Give unnecessary permissions

---

## Alternative: Using Service Account Key in Render

If environment variable method doesn't work, use this approach:

1. **Encode JSON to Base64**:
   ```bash
   # On Windows PowerShell:
   [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content google-credentials.json -Raw)))
   
   # On Linux/Mac:
   base64 google-credentials.json
   ```

2. **Add to Render**:
   - Environment variable: `GOOGLE_CREDENTIALS_BASE64`
   - Value: (paste base64 string)

3. **Update app.py** to decode:
   ```python
   import os
   import base64
   import json
   
   # Decode credentials
   if 'GOOGLE_CREDENTIALS_BASE64' in os.environ:
       creds_json = base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64'])
       with open('/tmp/google-creds.json', 'wb') as f:
           f.write(creds_json)
       os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/google-creds.json'
   ```

---

## Monitoring Usage

### Check API Usage:

1. Go to Google Cloud Console
2. Navigate to "APIs & Services" → "Dashboard"
3. Click on "Cloud Vision API"
4. View usage graphs and quotas

### Set Up Alerts:

1. Go to "Billing" → "Budgets & alerts"
2. Create budget alert
3. Set threshold (e.g., $5/month)
4. Get email when approaching limit

---

## What Gets Extracted

From your DCCCO form images, the system will extract:

### Page 1 - Personal Data:
- ✅ Applicant: Last Name, First Name, Middle Name, Birthday, Age
- ✅ Spouse: Last Name, First Name, Middle Name, Birthday, Age
- ✅ Family Background: Names, Ages, Relationships, Member Status

### Page 2 - Address:
- ✅ Purok, Barangay, Municipality, Province
- ✅ Full address string

### Page 3 - Financial:
- ✅ Income sources and amounts
- ✅ Expense items and amounts
- ✅ Total income and expenses

### Page 4 - Assets & Liabilities:
- ✅ Assets list
- ✅ Liabilities list
- ✅ Co-maker information
- ✅ References

### Page 5 - Additional:
- ✅ Any other text data from forms

---

## Support

### Google Cloud Support:
- Documentation: https://cloud.google.com/vision/docs
- Pricing: https://cloud.google.com/vision/pricing
- Support: https://cloud.google.com/support

### Common Issues:
- Check Google Cloud Status: https://status.cloud.google.com
- Community Forum: https://stackoverflow.com/questions/tagged/google-cloud-vision

---

## Summary Checklist

- [ ] Created Google Cloud account
- [ ] Created new project
- [ ] Enabled Cloud Vision API
- [ ] Created service account
- [ ] Downloaded JSON key file
- [ ] Added credentials to .env
- [ ] Added JSON file to .gitignore
- [ ] Installed dependencies (pip install)
- [ ] Tested OCR endpoint
- [ ] Uploaded test image
- [ ] Verified auto-fill works
- [ ] Configured Render environment variables (if deploying)

---

**Setup Time**: ~15 minutes
**Difficulty**: Easy
**Cost**: FREE for most use cases

**Status**: Ready to use! 🚀
