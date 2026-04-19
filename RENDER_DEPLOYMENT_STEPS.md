# Render Deployment Steps

## 📋 Pre-Deployment Checklist

- [x] All code changes committed
- [x] All routes tested locally
- [x] No syntax errors in Python files
- [x] JavaScript functions tested
- [x] Templates updated
- [x] Documentation complete

---

## 🚀 Deployment Process

### Step 1: Commit and Push to GitHub

```bash
# Check status
git status

# Add all modified files
git add templates/manage_users.html
git add app.py
git add templates/ci_checklist_summary_simple.html
git add static/ci-checklist-wizard.js
git add ROLE_MIGRATION_COMPLETE.md
git add DEPLOY_CHECKLIST.md
git add FINAL_STATUS_SUMMARY.md
git add QUICK_START_GUIDE.md
git add RENDER_DEPLOYMENT_STEPS.md

# Commit changes
git commit -m "Add role migration for active users and fix CI workflow"

# Push to GitHub
git push origin main
```

### Step 2: Render Auto-Deploy

1. Go to your Render dashboard: https://dashboard.render.com/
2. Select your service: **ci-staff-app-zag3**
3. Render will automatically detect the push and start deploying
4. Watch the deployment logs in real-time
5. Wait for "Build successful" and "Deploy live" messages

**Expected Deployment Time:** 2-5 minutes

---

## ⚙️ Environment Variables (Render)

### Required Variables

Go to your service → **Environment** tab and verify these are set:

1. **SECRET_KEY**
   - Value: (Your secret key)
   - Used for: Flask session security

2. **GOOGLE_APPLICATION_CREDENTIALS_JSON**
   - Value: (Contents of your Google Cloud credentials JSON file)
   - Used for: OCR functionality
   - Format: Paste the entire JSON file contents as a string

3. **RESEND_API_KEY**
   - Value: (Your Resend API key)
   - Used for: Email notifications

4. **FLASK_DEBUG**
   - Value: `False`
   - Used for: Production mode

### Optional Variables

5. **SEMAPHORE_API_KEY**
   - Value: (Your Semaphore API key)
   - Used for: SMS notifications (Philippines)

---

## 🔍 Monitoring Deployment

### Watch the Logs

In Render dashboard:
1. Click on your service
2. Go to **Logs** tab
3. Watch for these messages:

```
✓ Production users setup complete
✓ Created 18 default loan types
✓ Created 5 default system settings
 * Running on http://0.0.0.0:10000
```

### Check for Errors

Look for these error patterns:
- ❌ `ModuleNotFoundError` - Missing dependency
- ❌ `SyntaxError` - Code syntax error
- ❌ `ImportError` - Import issue
- ❌ `DatabaseError` - Database issue

If you see errors, check the **Troubleshooting** section below.

---

## ✅ Post-Deployment Verification

### Test 1: Basic Access
1. Visit: https://ci-staff-app-zag3.onrender.com/
2. ✅ Page loads without errors
3. ✅ Login page appears

### Test 2: Login
1. Login as admin: `admin@dccco.test` / `admin123`
2. ✅ Redirects to admin dashboard
3. ✅ No console errors

### Test 3: Role Migration
1. Go to **Manage Users**
2. Find an active user (not admin)
3. Change their role using dropdown
4. ✅ Confirmation dialog appears
5. ✅ Success notification shows
6. ✅ Page reloads
7. ✅ Role is updated

### Test 4: CI Workflow
1. Logout and login as CI Staff: `ci@dccco.test` / `ci123`
2. Go to **CI Dashboard**
3. Click **"Start"** on an application
4. ✅ Redirects to checkbox summary page
5. Fill some checkboxes
6. Click **"Proceed to 5-Page Form"**
7. ✅ Checkboxes are auto-filled (green highlight)
8. ✅ Form loads without errors

### Test 5: OCR (if credentials are set)
1. Logout and login as LPS: `loan@dccco.test` / `loan123`
2. Go to **Submit Application**
3. Upload an image
4. Click **"Extract Data from Images (AI)"**
5. ✅ Processing message appears
6. ✅ Data is extracted and filled

---

## 🐛 Troubleshooting

### Issue: Deployment Failed

**Symptoms:**
- Red "Deploy failed" message in Render
- Build errors in logs

**Solutions:**
1. Check logs for specific error message
2. Verify all files are committed and pushed
3. Check for syntax errors: `python -m py_compile app.py`
4. Verify requirements.txt is up to date
5. Try manual deploy: Click "Manual Deploy" → "Deploy latest commit"

### Issue: 500 Internal Server Error

**Symptoms:**
- Page shows "Internal Server Error"
- Application crashes on certain pages

**Solutions:**
1. Check Render logs for Python traceback
2. Verify environment variables are set correctly
3. Check database connection
4. Verify all templates exist
5. Check for missing imports

### Issue: Role Dropdown Not Appearing

**Symptoms:**
- Active users don't have role dropdown
- Only pending users have dropdown

**Solutions:**
1. Clear browser cache (Ctrl+Shift+R)
2. Check browser console for JavaScript errors
3. Verify `manage_users.html` was deployed
4. Check if user is logged in as admin/loan officer

### Issue: CI Workflow Redirects to Wrong Page

**Symptoms:**
- Clicking "Start" shows error
- Redirects to wrong page

**Solutions:**
1. Check Render logs for route errors
2. Verify routes in app.py:
   - `/ci/checklist/<id>` (GET) exists
   - `/ci/checklist/summary/<id>` exists
   - `/ci/checklist/wizard/<id>` exists
3. Check for duplicate function definitions
4. Verify templates exist

### Issue: Checkboxes Not Auto-Filling

**Symptoms:**
- Wizard loads but checkboxes are empty
- No green highlight

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify `ci-checklist-wizard.js` was deployed
3. Check sessionStorage in browser DevTools
4. Verify `loadCheckboxData()` function exists

### Issue: OCR Not Working

**Symptoms:**
- "Extract Data" button does nothing
- Error message appears

**Solutions:**
1. Verify `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set in Render
2. Check Render logs for Google Cloud API errors
3. Verify credentials JSON is valid
4. Check if Google Cloud Vision API is enabled
5. Verify billing is enabled on Google Cloud project

---

## 🔄 Rollback Procedure

If deployment causes critical issues:

### Option 1: Quick Rollback (Render Dashboard)
1. Go to Render dashboard
2. Select your service
3. Click **"Events"** tab
4. Find previous successful deployment
5. Click **"Rollback to this version"**
6. Confirm rollback
7. Wait for rollback to complete (1-2 minutes)

### Option 2: Git Rollback
```bash
# Find the commit to rollback to
git log --oneline

# Rollback to previous commit
git revert HEAD

# Or reset to specific commit
git reset --hard <commit-hash>

# Force push
git push origin main --force
```

---

## 📊 Success Metrics

After deployment, verify these metrics:

- ✅ Deployment status: **Live**
- ✅ Health check: **Passing**
- ✅ Response time: **< 2 seconds**
- ✅ Error rate: **0%**
- ✅ All test cases: **Passing**

---

## 📞 Support Contacts

### Render Support
- Dashboard: https://dashboard.render.com/
- Docs: https://render.com/docs
- Status: https://status.render.com/

### Google Cloud Support
- Console: https://console.cloud.google.com/
- Vision API: https://cloud.google.com/vision/docs
- Support: https://cloud.google.com/support

---

## 📝 Deployment Log Template

Use this template to track your deployment:

```
Deployment Date: 2026-04-19
Deployment Time: [TIME]
Deployed By: [YOUR NAME]
Commit Hash: [COMMIT HASH]
Branch: main

Changes Deployed:
- Role migration for active users
- CI workflow fixes (checkbox summary)
- OCR auto-fill integration
- LPS edit functionality
- Loan officer "In Process" tab

Pre-Deployment Tests:
- [x] Local testing complete
- [x] All routes verified
- [x] JavaScript functions tested
- [x] Templates updated

Post-Deployment Tests:
- [ ] Basic access
- [ ] Login functionality
- [ ] Role migration
- [ ] CI workflow
- [ ] OCR functionality

Issues Encountered:
[NONE / LIST ISSUES]

Resolution:
[N/A / DESCRIBE RESOLUTION]

Status: SUCCESS / FAILED
Notes: [ANY ADDITIONAL NOTES]
```

---

## 🎉 Deployment Complete!

Once all tests pass:

1. ✅ Notify users of new features
2. ✅ Update user documentation
3. ✅ Monitor logs for 24 hours
4. ✅ Gather user feedback
5. ✅ Plan next iteration

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2026-04-19
**Status:** Ready to Deploy
