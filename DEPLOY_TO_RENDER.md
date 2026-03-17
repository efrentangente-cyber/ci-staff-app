# Deploy to Render.com - Simple Guide

## What You'll Get
- Your app online at: `https://your-app-name.onrender.com`
- Free HTTPS (secure connection)
- Automatic restarts if it crashes
- Free tier (sleeps after 15 min, wakes in 30 sec)

---

## PART 1: Upload Your Code to GitHub (Simple Way)

### Option A: Use GitHub Desktop (EASIEST - NO COMMANDS)

1. **Download GitHub Desktop**
   - Go to: https://desktop.github.com/
   - Download and install

2. **Create GitHub Account** (if you don't have one)
   - Go to: https://github.com/signup
   - Create free account

3. **In GitHub Desktop:**
   - Click "File" → "Add Local Repository"
   - Browse to: `C:\xampp2\htdocs\geo_smart_ci`
   - Click "Add Repository"
   
4. **If it says "not a git repository":**
   - Click "Create a repository instead"
   - Name: `dccco-ci-system`
   - Click "Create Repository"

5. **Publish to GitHub:**
   - Click "Publish repository" button (top right)
   - Uncheck "Keep this code private" (or keep it private, your choice)
   - Click "Publish Repository"

**DONE!** Your code is now on GitHub.

---

### Option B: Use Git Commands (If you prefer terminal)

```bash
# 1. Initialize git (only first time)
git init

# 2. Add all files
git add .

# 3. Commit files
git commit -m "Initial commit - DCCCO CI System"

# 4. Create repository on GitHub.com first, then:
git remote add origin https://github.com/YOUR-USERNAME/dccco-ci-system.git
git branch -M main
git push -u origin main
```

---

## PART 2: Deploy to Render (Super Easy)

### Step 1: Create Render Account
1. Go to: https://render.com/
2. Click "Get Started for Free"
3. Sign up with GitHub (click "Sign up with GitHub")
4. Authorize Render to access your GitHub

### Step 2: Create New Web Service
1. Click "New +" button (top right)
2. Select "Web Service"
3. Click "Connect" next to your `dccco-ci-system` repository
4. If you don't see it, click "Configure account" and give Render access

### Step 3: Configure Your Service

Fill in these settings:

**Name:** `dccco-ci-system` (or whatever you want)

**Region:** Choose closest to Philippines (Singapore recommended)

**Branch:** `main`

**Runtime:** `Python 3`

**Build Command:** 
```
pip install -r requirements.txt
```

**Start Command:**
```
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

**Instance Type:** `Free`

### Step 4: Add Environment Variables

Click "Advanced" → "Add Environment Variable"

Add these ONE BY ONE:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `70d7d6bf2d6f3ddb2b3ac3d414e7ea15d56fbe07014a5804923bd3631d509891` |
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `False` |
| `RESEND_API_KEY` | `re_hKeBgyYW_NwHJCrrsw7FEJYWmNRkcAPwF` |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` |

### Step 5: Add Persistent Disk (IMPORTANT!)

Scroll down to "Disks" section:
- Click "Add Disk"
- **Name:** `data`
- **Mount Path:** `/opt/render/project/src`
- **Size:** `1 GB` (free tier)
- Click "Save"

This keeps your database and uploaded files safe!

### Step 6: Deploy!

1. Click "Create Web Service" button at bottom
2. Wait 5-10 minutes while Render builds your app
3. Watch the logs - you'll see it installing packages
4. When you see "Your service is live 🎉" - YOU'RE DONE!

---

## PART 3: Access Your App

Your app will be at:
```
https://dccco-ci-system.onrender.com
```
(Replace `dccco-ci-system` with whatever name you chose)

### First Time Setup:

1. Go to your URL
2. Login with:
   - Email: `admin@dccco.test`
   - Password: `admin123`

3. **IMPORTANT:** Change the admin password immediately!

---

## PART 4: Update WebSocket CORS

After deployment, you need to update one thing:

1. In Render dashboard, go to "Environment"
2. Add new environment variable:
   - Key: `RENDER_EXTERNAL_URL`
   - Value: Your render URL (e.g., `https://dccco-ci-system.onrender.com`)

3. Then update `app.py` line ~60:

**Change from:**
```python
socketio = SocketIO(app, cors_allowed_origins=[
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://192.168.1.61:5000",
    "http://192.168.1.41:5000"
])
```

**Change to:**
```python
import os
allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

# Add Render URL if deployed
render_url = os.getenv('RENDER_EXTERNAL_URL')
if render_url:
    allowed_origins.append(render_url)
    allowed_origins.append(render_url.replace('https://', 'http://'))

socketio = SocketIO(app, cors_allowed_origins=allowed_origins)
```

4. Commit and push changes (Render auto-deploys)

---

## Troubleshooting

### "Application failed to start"
- Check logs in Render dashboard
- Make sure all environment variables are set
- Verify disk is attached

### "Database is locked"
- This is normal on first deploy
- Wait 1 minute and refresh

### "Can't connect to WebSocket"
- Make sure you updated CORS settings
- Check RENDER_EXTERNAL_URL is set

### "Free tier sleeping"
- Free apps sleep after 15 min inactivity
- First request takes 30 seconds to wake up
- Upgrade to $7/month for always-on

---

## Updating Your App

When you make changes:

**Using GitHub Desktop:**
1. Make changes to your code
2. Open GitHub Desktop
3. Write commit message (e.g., "Fixed bug")
4. Click "Commit to main"
5. Click "Push origin"
6. Render automatically redeploys!

**Using Git Commands:**
```bash
git add .
git commit -m "Your change description"
git push
```

Render detects the push and redeploys automatically!

---

## Cost Breakdown

**Free Tier:**
- ✅ 750 hours/month (enough for testing)
- ✅ Sleeps after 15 min inactivity
- ✅ 1GB disk storage
- ✅ HTTPS included

**Paid Tier ($7/month):**
- ✅ Always on (no sleeping)
- ✅ Faster performance
- ✅ More disk storage options

---

## Need Help?

If you get stuck:
1. Check Render logs (click "Logs" tab)
2. Check GitHub repository is public or Render has access
3. Verify all environment variables are set
4. Make sure disk is attached

---

## Summary

1. ✅ Upload code to GitHub (use GitHub Desktop - easiest)
2. ✅ Create Render account
3. ✅ Connect GitHub repository
4. ✅ Configure settings (copy from this guide)
5. ✅ Add environment variables
6. ✅ Add persistent disk
7. ✅ Click "Create Web Service"
8. ✅ Wait 5-10 minutes
9. ✅ Your app is LIVE!

**Your app will be at:** `https://your-app-name.onrender.com`

🎉 That's it! Your DCCCO CI System is now online!
