# Render Deployment Checklist ✅

Use this checklist to make sure you don't miss anything!

---

## Before You Start

- [ ] Your app works locally (run `python app.py` to test)
- [ ] You have a GitHub account (create at github.com/signup)
- [ ] You have a Render account (create at render.com)

---

## Step 1: GitHub (Choose ONE method)

### Method A: GitHub Desktop (Recommended - No Commands)
- [ ] Download GitHub Desktop from desktop.github.com
- [ ] Install and sign in
- [ ] Add your project folder
- [ ] Publish to GitHub

### Method B: Git Commands
- [ ] Run `git init`
- [ ] Run `git add .`
- [ ] Run `git commit -m "Initial commit"`
- [ ] Create repo on GitHub.com
- [ ] Run `git remote add origin YOUR-REPO-URL`
- [ ] Run `git push -u origin main`

---

## Step 2: Render Setup

- [ ] Go to render.com
- [ ] Sign up with GitHub
- [ ] Click "New +" → "Web Service"
- [ ] Connect your repository

---

## Step 3: Configure Service

- [ ] Name: `dccco-ci-system` (or your choice)
- [ ] Region: Singapore (closest to Philippines)
- [ ] Branch: `main`
- [ ] Runtime: `Python 3`
- [ ] Build Command: `pip install -r requirements.txt`
- [ ] Start Command: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
- [ ] Instance Type: `Free`

---

## Step 4: Environment Variables

Add these in "Advanced" → "Environment Variables":

- [ ] `SECRET_KEY` = `70d7d6bf2d6f3ddb2b3ac3d414e7ea15d56fbe07014a5804923bd3631d509891`
- [ ] `FLASK_ENV` = `production`
- [ ] `FLASK_DEBUG` = `False`
- [ ] `RESEND_API_KEY` = `re_hKeBgyYW_NwHJCrrsw7FEJYWmNRkcAPwF`
- [ ] `RESEND_FROM_EMAIL` = `onboarding@resend.dev`

---

## Step 5: Add Disk Storage

- [ ] Scroll to "Disks" section
- [ ] Click "Add Disk"
- [ ] Name: `data`
- [ ] Mount Path: `/opt/render/project/src`
- [ ] Size: `1 GB`
- [ ] Click "Save"

---

## Step 6: Deploy

- [ ] Click "Create Web Service"
- [ ] Wait 5-10 minutes
- [ ] Watch logs for "Your service is live 🎉"

---

## Step 7: Test Your App

- [ ] Open your Render URL (e.g., https://dccco-ci-system.onrender.com)
- [ ] Login with admin@dccco.test / admin123
- [ ] Test creating a loan application
- [ ] Test file upload
- [ ] Test real-time updates

---

## Step 8: Post-Deployment

- [ ] Change admin password
- [ ] Add RENDER_EXTERNAL_URL environment variable with your app URL
- [ ] Test from mobile device
- [ ] Share URL with your team

---

## Common Issues

### ❌ "Application failed to start"
**Fix:** Check logs, verify all environment variables are set

### ❌ "Database is locked"
**Fix:** Wait 1 minute, refresh page

### ❌ "Can't upload files"
**Fix:** Make sure disk is attached in Render settings

### ❌ "WebSocket not connecting"
**Fix:** Add RENDER_EXTERNAL_URL environment variable

---

## Your App URLs

**Local (development):**
- http://localhost:5000
- http://192.168.1.61:5000

**Production (Render):**
- https://YOUR-APP-NAME.onrender.com

---

## Need Help?

Read the full guide: `DEPLOY_TO_RENDER.md`

---

## Done! 🎉

Once all checkboxes are checked, your app is live and accessible from anywhere!
