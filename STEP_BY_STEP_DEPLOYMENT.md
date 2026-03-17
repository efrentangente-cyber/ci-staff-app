# Complete Step-by-Step Deployment Guide

Follow these steps EXACTLY. Don't skip any step.

---

## PHASE 1: GITHUB SETUP (10 minutes)

### Step 1: Download GitHub Desktop
1. Open your web browser
2. Go to: **https://desktop.github.com/**
3. Click the big "Download for Windows" button
4. Wait for download to finish
5. Double-click the downloaded file
6. Click "Install" (it installs automatically)
7. Wait until you see "GitHub Desktop" open

✅ **Done? Check:** You should see GitHub Desktop app open

---

### Step 2: Create GitHub Account
1. In your web browser, go to: **https://github.com/signup**
2. Enter your email address
3. Click "Continue"
4. Create a password (write it down!)
5. Create a username (example: `dccco-admin`)
6. Click "Continue"
7. Solve the puzzle
8. Click "Create account"
9. Check your email for verification code
10. Enter the code
11. Click "Continue"

✅ **Done? Check:** You should see "Welcome to GitHub" page

---

### Step 3: Sign In to GitHub Desktop
1. Go back to GitHub Desktop app
2. Click "Sign in to GitHub.com"
3. It opens your browser
4. Click "Authorize desktop"
5. Enter your GitHub password if asked
6. Go back to GitHub Desktop
7. Click "Finish"

✅ **Done? Check:** You should see your username in GitHub Desktop

---

### Step 4: Configure Git
1. In GitHub Desktop, you'll see "Configure Git"
2. Enter your name (example: `DCCCO Admin`)
3. Enter your email (same as GitHub account)
4. Click "Finish"

✅ **Done? Check:** You should see the main GitHub Desktop screen

---

### Step 5: Add Your Project
1. In GitHub Desktop, click **"File"** menu (top left)
2. Click **"Add local repository"**
3. Click the **"Choose..."** button
4. Navigate to: `C:\xampp2\htdocs\geo_smart_ci`
5. Click **"Select Folder"**

You'll see a message: "This directory does not appear to be a Git repository"

6. Click **"create a repository"** link (blue text)

✅ **Done? Check:** You should see "Create a Repository" dialog

---

### Step 6: Create Repository
1. In the "Create a Repository" dialog:
   - **Name:** Change to `DCCCOfinal`
   - **Description:** `DCCCO CI Staff Loan Management System`
   - **Local Path:** Should show `C:\xampp2\htdocs\geo_smart_ci`
   - **Git Ignore:** Leave as "None"
   - **License:** Leave as "None"
   - **Initialize with README:** UNCHECK this box

2. Click **"Create Repository"** button

✅ **Done? Check:** You should see a list of files in GitHub Desktop

---

### Step 7: Review Files to Upload
1. Look at the left side of GitHub Desktop
2. You should see many files listed
3. **IMPORTANT:** You should NOT see:
   - ❌ `app.db`
   - ❌ Files in `uploads/` folder
   - ❌ `ngrok.exe`
   - ❌ `.env` file

4. You SHOULD see:
   - ✅ `app.py`
   - ✅ `requirements.txt`
   - ✅ Files in `templates/` folder
   - ✅ Files in `static/` folder
   - ✅ `.gitignore` file

✅ **Done? Check:** Files look correct (no database, no uploads)

---

### Step 8: Make First Commit
1. At the bottom left, you'll see "Summary (required)"
2. Type: `Initial commit - DCCCO CI System`
3. Click the blue **"Commit to main"** button
4. Wait 5-10 seconds

✅ **Done? Check:** The file list should disappear (all committed)

---

### Step 9: Publish to GitHub
1. Click the big blue **"Publish repository"** button (top right)
2. A dialog appears:
   - **Name:** `dccco-ci-system`
   - **Description:** (already filled)
   - **Keep this code private:** UNCHECK this (or keep checked if you want private)
   - **Organization:** Leave as "None"

3. Click **"Publish Repository"** button
4. Wait 2-5 minutes (it's uploading your code)
5. You'll see a progress bar

✅ **Done? Check:** You should see "Last fetched just now" at the top

---

### Step 10: Verify on GitHub.com
1. In GitHub Desktop, click **"Repository"** menu
2. Click **"View on GitHub"**
3. Your browser opens showing your code on GitHub.com
4. You should see all your files listed

✅ **Done? Check:** You can see your code on GitHub.com

---

## PHASE 2: RENDER DEPLOYMENT (15 minutes)

### Step 11: Create Render Account
1. Open your browser
2. Go to: **https://render.com/**
3. Click **"Get Started for Free"**
4. Click **"Sign up with GitHub"** (the GitHub icon)
5. Click **"Authorize Render"**
6. Enter your GitHub password if asked
7. Click **"Authorize render"**

✅ **Done? Check:** You should see Render dashboard

---

### Step 12: Create New Web Service
1. In Render dashboard, click the **"New +"** button (top right)
2. Click **"Web Service"**
3. You'll see "Create a new Web Service"
4. Look for your repository: `dccco-ci-system`
5. Click **"Connect"** button next to it

**If you don't see your repository:**
- Click "Configure account" link
- Give Render access to your repositories
- Go back and refresh

✅ **Done? Check:** You should see "Configure Web Service" page

---

### Step 13: Configure Basic Settings
Fill in these fields:

1. **Name:** `dccco-ci-system` (or choose your own)
   - This will be your URL: `https://dccco-ci-system.onrender.com`

2. **Region:** Select **"Singapore"** (closest to Philippines)

3. **Branch:** `main` (should be selected)

4. **Root Directory:** Leave EMPTY

5. **Runtime:** Select **"Python 3"**

6. **Build Command:** 
   ```
   pip install -r requirements.txt
   ```
   (Copy and paste this exactly)

7. **Start Command:**
   ```
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
   ```
   (Copy and paste this exactly)

✅ **Done? Check:** All fields filled correctly

---

### Step 14: Select Instance Type
1. Scroll down to "Instance Type"
2. Select **"Free"**
3. You'll see "$0/month"

✅ **Done? Check:** Free tier selected

---

### Step 15: Add Environment Variables
1. Click **"Advanced"** button (below Instance Type)
2. Scroll to "Environment Variables" section
3. Click **"Add Environment Variable"**

Add these ONE BY ONE (click "Add Environment Variable" for each):

**Variable 1:**
- Key: `SECRET_KEY`
- Value: `70d7d6bf2d6f3ddb2b3ac3d414e7ea15d56fbe07014a5804923bd3631d509891`

**Variable 2:**
- Key: `FLASK_ENV`
- Value: `production`

**Variable 3:**
- Key: `FLASK_DEBUG`
- Value: `False`

**Variable 4:**
- Key: `RESEND_API_KEY`
- Value: `re_hKeBgyYW_NwHJCrrsw7FEJYWmNRkcAPwF`

**Variable 5:**
- Key: `RESEND_FROM_EMAIL`
- Value: `onboarding@resend.dev`

✅ **Done? Check:** You should have 5 environment variables

---

### Step 16: Add Persistent Disk (IMPORTANT!)
1. Still in "Advanced" section, scroll to **"Disks"**
2. Click **"Add Disk"** button
3. Fill in:
   - **Name:** `data`
   - **Mount Path:** `/opt/render/project/src`
   - **Size:** `1` GB

4. Click **"Save"**

✅ **Done? Check:** You should see disk listed with 1 GB

---

### Step 17: Create Web Service
1. Scroll all the way down
2. Click the big blue **"Create Web Service"** button
3. Wait for deployment to start

✅ **Done? Check:** You should see "Deploying..." with logs

---

### Step 18: Watch Deployment Logs
You'll see logs scrolling. Wait for these messages:

```
==> Installing dependencies...
==> Building...
==> Starting service...
==> Your service is live 🎉
```

This takes **5-10 minutes**. Be patient!

✅ **Done? Check:** You see "Your service is live 🎉"

---

### Step 19: Get Your URL
1. At the top of the page, you'll see your URL
2. It looks like: `https://dccco-ci-system.onrender.com`
3. Click on it to open your app

✅ **Done? Check:** Your app opens in browser

---

### Step 20: First Login
1. You should see your login page
2. Login with:
   - **Email:** `admin@dccco.test`
   - **Password:** `admin123`

3. Click "Login"

✅ **Done? Check:** You should see the admin dashboard

---

## PHASE 3: POST-DEPLOYMENT (5 minutes)

### Step 21: Change Admin Password
1. In your app, click your name (top right)
2. Click "Change Password"
3. Enter:
   - Current password: `admin123`
   - New password: (choose a strong one - 8+ chars, uppercase, lowercase, number)
   - Confirm password: (same as above)
4. Click "Update Password"

✅ **Done? Check:** Password changed successfully

---

### Step 22: Add Render URL to Environment
1. Go back to Render dashboard
2. Click on your service name
3. Click **"Environment"** tab (left side)
4. Click **"Add Environment Variable"**
5. Add:
   - Key: `RENDER_EXTERNAL_URL`
   - Value: Your full URL (e.g., `https://dccco-ci-system.onrender.com`)
6. Click "Save Changes"
7. Your app will redeploy (wait 2-3 minutes)

✅ **Done? Check:** Environment variable added

---

### Step 23: Test Your App
Test these features:

1. **Login/Logout** - Works?
2. **Create loan application** - Works?
3. **Upload document** - Works?
4. **Real-time updates** - Works?
5. **Access from phone** - Works?

✅ **Done? Check:** Everything works!

---

### Step 24: Share with Your Team
1. Copy your URL: `https://your-app-name.onrender.com`
2. Share with your team
3. They can access from anywhere!

✅ **Done? Check:** Team can access the app

---

## TROUBLESHOOTING

### Problem: "Application failed to start"
**Solution:**
1. Check logs in Render dashboard
2. Verify all 5 environment variables are set
3. Check disk is attached

### Problem: "Database is locked"
**Solution:**
1. Wait 1 minute
2. Refresh the page
3. This is normal on first deploy

### Problem: "Can't upload files"
**Solution:**
1. Check disk is attached in Render
2. Verify mount path is `/opt/render/project/src`

### Problem: "Free tier sleeping"
**Solution:**
1. This is normal - free apps sleep after 15 min
2. First request takes 30 seconds to wake up
3. Upgrade to $7/month for always-on

---

## UPDATING YOUR APP LATER

When you make changes to your code:

1. Open GitHub Desktop
2. You'll see your changes listed
3. Type what you changed (e.g., "Fixed bug")
4. Click "Commit to main"
5. Click "Push origin"
6. Render automatically redeploys!

---

## SUMMARY

✅ **Phase 1:** Code uploaded to GitHub  
✅ **Phase 2:** App deployed to Render  
✅ **Phase 3:** App configured and tested  

**Your app is now LIVE at:** `https://your-app-name.onrender.com`

🎉 **CONGRATULATIONS!** Your DCCCO CI System is online!

---

## NEED HELP?

If you get stuck on any step:
1. Read the error message carefully
2. Check the troubleshooting section above
3. Verify you followed each step exactly
4. Check Render logs for errors

---

**Total Time:** 30 minutes  
**Cost:** FREE  
**Result:** Your app accessible from anywhere!
