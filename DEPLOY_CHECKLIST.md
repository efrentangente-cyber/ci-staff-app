# Deployment Checklist - Role Migration & CI Workflow

## Pre-Deployment Verification

### 1. Files to Deploy
- ✅ `templates/manage_users.html` - Role migration UI for active users
- ✅ `app.py` - CI workflow routes (already correct)
- ✅ `templates/ci_checklist_summary_simple.html` - Checkbox summary page
- ✅ `static/ci-checklist-wizard.js` - Auto-load checkbox and OCR data

### 2. Database Requirements
- ✅ No database migrations needed
- ✅ Uses existing `users` table with `role` and `assigned_route` columns
- ✅ Uses existing `/assign_role` endpoint

### 3. Environment Variables
- ✅ No new environment variables needed
- ✅ Existing variables should be set:
  - `SECRET_KEY`
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (for OCR)
  - `RESEND_API_KEY` (for emails)

## Deployment Steps

### Step 1: Commit Changes
```bash
git add templates/manage_users.html
git add ROLE_MIGRATION_COMPLETE.md
git add DEPLOY_CHECKLIST.md
git commit -m "Add role migration for active users in Manage Users"
git push origin main
```

### Step 2: Deploy to Render
1. Go to Render dashboard
2. Select your service
3. Render will auto-deploy from GitHub
4. Wait for deployment to complete
5. Check deployment logs for errors

### Step 3: Verify Deployment
1. Visit: https://ci-staff-app-zag3.onrender.com/
2. Login as admin or loan officer
3. Go to Manage Users
4. Verify role dropdowns appear for active users

## Post-Deployment Testing

### Test 1: Role Migration for Active Users
1. Login as admin: `admin@dccco.test` / `admin123`
2. Go to Manage Users
3. Find an active user (e.g., loan staff or CI staff)
4. Change their role using dropdown
5. Confirm the change
6. ✅ Verify success notification
7. ✅ Verify page reloads
8. ✅ Verify role is updated

### Test 2: CI Workflow - Complete End-to-End
1. Login as LPS: `loan@dccco.test` / `loan123`
2. Submit a new loan application
3. Logout and login as CI Staff: `ci@dccco.test` / `ci123`
4. Go to CI Dashboard
5. Click "Start" on the application
6. ✅ Verify redirects to checkbox summary page
7. Fill some checkboxes
8. Click "Proceed to 5-Page Form"
9. ✅ Verify checkboxes are auto-filled (green highlight)
10. Complete the wizard
11. Submit the checklist
12. ✅ Verify data is saved
13. ✅ Verify application status is updated

### Test 3: Role Migration with Route Assignment
1. Login as admin
2. Go to Manage Users
3. Change a user's role to "CI Staff"
4. ✅ Verify route dropdown appears (if not already assigned)
5. Assign a route
6. Change role back to "LPS"
7. ✅ Verify route is cleared

### Test 4: Authorization
1. Try to access Manage Users as LPS
2. ✅ Verify access is denied
3. Try to access Manage Users as CI Staff
4. ✅ Verify access is denied
5. Only admin and loan officer should have access

## Rollback Plan

If issues occur:

### Option 1: Quick Fix
1. Identify the issue in logs
2. Fix the code
3. Push and redeploy

### Option 2: Rollback
1. Go to Render dashboard
2. Select your service
3. Go to "Events" tab
4. Find previous successful deployment
5. Click "Rollback to this version"

## Known Issues & Solutions

### Issue 1: Dropdown doesn't appear for active users
**Solution:** Clear browser cache and hard refresh (Ctrl+Shift+R)

### Issue 2: Role change doesn't persist
**Solution:** Check database connection and `/assign_role` endpoint logs

### Issue 3: CI workflow redirects to wrong page
**Solution:** Verify routes in app.py:
- `/ci/checklist/<id>` (GET) → redirects to summary
- `/ci/checklist/summary/<id>` → renders summary page
- `/ci/checklist/wizard/<id>` → renders wizard

### Issue 4: Checkboxes not auto-filling in wizard
**Solution:** Check browser console for JavaScript errors. Verify sessionStorage is working.

## Success Criteria

✅ Admin/Loan Officer can change roles for active users
✅ Confirmation dialog appears before role change
✅ Success notification appears after role change
✅ Page reloads automatically
✅ CI workflow: Dashboard → Summary → Wizard works
✅ Checkboxes auto-fill in wizard from summary
✅ OCR data auto-fills in wizard (if available)
✅ No console errors
✅ No server errors in logs

## Monitoring

After deployment, monitor:
1. Render logs for errors
2. User feedback
3. Database for correct role updates
4. CI workflow completion rates

## Support

If issues persist:
1. Check Render logs
2. Check browser console
3. Verify database state
4. Contact support with error details

---

**Deployment Date:** 2026-04-19
**Status:** Ready to Deploy
**Estimated Downtime:** None (zero-downtime deployment)
