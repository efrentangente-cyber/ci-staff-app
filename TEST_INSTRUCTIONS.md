# Quick Test Instructions

## Test 1: LPS Edit Application (2 minutes)

### Setup
- Login as: LPS (loan_staff role)
- URL: https://ci-staff-app-zag3.onrender.com/

### Steps
1. Click "Submit New Application"
2. Fill form and submit
3. Click on the application from dashboard
4. ✅ Verify: Form shows with all fields editable
5. Change member name to "Test Edit"
6. Change loan amount to "75,000"
7. Click "Update Application"
8. ✅ Verify: Success message shows
9. ✅ Verify: Changes saved (name and amount updated)

### Expected Result
- Form is editable
- All fields pre-filled
- Update saves successfully
- Success message appears

---

## Test 2: LPS Cannot Edit After CI (1 minute)

### Setup
- Need an application that CI has completed
- Login as: LPS

### Steps
1. Click on application with status "CI Completed"
2. ✅ Verify: Alert shows "cannot be edited"
3. ✅ Verify: All fields are read-only (gray)
4. ✅ Verify: No "Update" button, only "Back"

### Expected Result
- Form is read-only
- Alert message visible
- No edit capability

---

## Test 3: View In Process Tab (1 minute)

### Setup
- Login as: Loan Officer (admin role)
- URL: https://ci-staff-app-zag3.onrender.com/admin/dashboard

### Steps
1. Look for "In Process (LPS → CI)" section
2. ✅ Verify: Section exists between CI Staff and For Review
3. ✅ Verify: Shows applications with "Submitted" or "Assigned to CI" status
4. ✅ Verify: Columns: Member Name, Amount, Status, LPS, CI Staff, Submitted, Actions
5. ✅ Verify: "Reassign CI" button on each row
6. ✅ Verify: Search box present
7. ✅ Verify: Badge shows count

### Expected Result
- "In Process" tab visible
- Applications listed correctly
- All UI elements present

---

## Test 4: Reassign CI Staff (2 minutes)

### Setup
- Login as: Loan Officer
- Need at least one application in "In Process" tab

### Steps
1. Go to "In Process" tab
2. Click "Reassign CI" button on any application
3. ✅ Verify: Modal opens
4. ✅ Verify: Shows application member name
5. ✅ Verify: Dropdown shows all CI staff
6. ✅ Verify: Current CI staff is pre-selected
7. Select different CI staff
8. Click "Reassign"
9. ✅ Verify: Success message appears
10. ✅ Verify: Page reloads
11. ✅ Verify: CI Staff column updated

### Expected Result
- Modal opens correctly
- Reassignment processes
- Success message shows
- Data updates immediately

---

## Test 5: Search In Process (1 minute)

### Setup
- Login as: Loan Officer
- In "In Process" tab

### Steps
1. Type member name in search box
2. ✅ Verify: Table filters to matching rows
3. ✅ Verify: Badge count updates
4. ✅ Verify: Clear button (X) appears
5. Click clear button
6. ✅ Verify: All rows show again
7. ✅ Verify: Badge count resets

### Expected Result
- Search filters correctly
- Clear button works
- Count updates dynamically

---

## Test 6: Tab Separation (1 minute)

### Setup
- Login as: Loan Officer
- Have applications in different statuses

### Steps
1. Check "In Process" tab
   - ✅ Should show: 'submitted', 'assigned_to_ci'
2. Check "For Review" tab
   - ✅ Should show: 'ci_completed'
3. Check "Processed" tab
   - ✅ Should show: 'approved', 'disapproved'
4. ✅ Verify: No application appears in multiple tabs

### Expected Result
- Each tab shows correct statuses
- No overlap between tabs
- Counts are accurate

---

## Quick Smoke Test (30 seconds)

### All Features Working?
1. Login as LPS → Can see applications → ✅
2. Click application → Form loads → ✅
3. Login as Loan Officer → Dashboard loads → ✅
4. "In Process" tab visible → ✅
5. "Reassign CI" button present → ✅

If all ✅, deployment successful!

---

## Troubleshooting

### Issue: Form not editable
**Check:**
- Application status (must be 'submitted' or 'assigned_to_ci')
- User role (must be loan_staff who submitted)
- Browser console for errors

### Issue: In Process tab not showing
**Check:**
- User role (must be admin or loan_officer)
- Browser cache (hard refresh: Ctrl+Shift+R)
- Check if in_process_applications passed to template

### Issue: Reassign not working
**Check:**
- Network tab for failed requests
- Check `/reassign_ci_staff/<id>` endpoint exists
- Verify CI staff ID is valid

### Issue: Search not filtering
**Check:**
- JavaScript console for errors
- Verify table ID is 'inProcessTable'
- Check searchApplications('inprocess') function

---

## Test Data Setup

### Create Test Applications
```sql
-- Application 1: Submitted (should show in In Process)
INSERT INTO loan_applications (member_name, loan_amount, status, submitted_by)
VALUES ('Test User 1', 50000, 'submitted', 3);

-- Application 2: Assigned to CI (should show in In Process)
INSERT INTO loan_applications (member_name, loan_amount, status, submitted_by, assigned_ci_staff)
VALUES ('Test User 2', 30000, 'assigned_to_ci', 3, 4);

-- Application 3: CI Completed (should show in For Review)
INSERT INTO loan_applications (member_name, loan_amount, status, submitted_by, assigned_ci_staff)
VALUES ('Test User 3', 40000, 'ci_completed', 3, 4);

-- Application 4: Approved (should show in Processed)
INSERT INTO loan_applications (member_name, loan_amount, status, submitted_by)
VALUES ('Test User 4', 60000, 'approved', 3);
```

---

## Success Criteria

### All Tests Pass If:
- ✅ LPS can edit applications before CI completes
- ✅ LPS cannot edit after CI completes
- ✅ "In Process" tab shows correct applications
- ✅ Reassign CI staff works
- ✅ Search filters correctly
- ✅ Tabs show correct statuses
- ✅ No errors in browser console
- ✅ Notifications sent correctly

---

## Test Results Template

```
Date: _______________
Tester: _______________

Test 1 - LPS Edit: [ ] PASS [ ] FAIL
Test 2 - Cannot Edit After CI: [ ] PASS [ ] FAIL
Test 3 - In Process Tab: [ ] PASS [ ] FAIL
Test 4 - Reassign CI: [ ] PASS [ ] FAIL
Test 5 - Search: [ ] PASS [ ] FAIL
Test 6 - Tab Separation: [ ] PASS [ ] FAIL

Issues Found:
_________________________________
_________________________________
_________________________________

Overall Status: [ ] READY [ ] NEEDS FIX
```

---

**Total Test Time:** ~8 minutes
**Recommended:** Test after each deployment
**Priority:** High (core functionality)
