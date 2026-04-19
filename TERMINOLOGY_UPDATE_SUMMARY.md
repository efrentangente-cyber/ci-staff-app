# Terminology Update Summary

## Changes Required

### 1. "Loan Staff" → "LPS" (Loan Processing Staff)
**Files to update:**
- templates/admin_dashboard.html (2 occurrences in table headers)
- templates/loan_dashboard.html (page title)
- templates/admin_application.html ("Submitted By" label)
- templates/manage_users.html (dropdown option)
- templates/reports.html (dropdown option)
- All setup/check scripts (display names only, not role values)

**Note:** Keep `role='loan_staff'` in database - only change display text

### 2. "Reject/Rejected" → "Disapprove/Disapproved"
**Files to update:**
- schema.sql: ✅ DONE - Updated status CHECK constraint
- app.py: All flash messages and status checks
- templates/admin_application.html: Decision form options
- Database: ✅ DONE - Updated existing records

### 3. Add "Defer" Option
**Files to update:**
- schema.sql: ✅ DONE - Added 'deferred' to status CHECK
- templates/admin_application.html: Add "Defer" option to decision form
- app.py: Handle 'deferred' status in admin_application route

### 4. Add CI Staff Reassignment
**New functionality needed:**
- Add "Reassign CI Staff" button/dropdown in admin view
- Allow changing CI staff even if already assigned
- Update workload counts when reassigning
- Send notifications to new CI staff

### 5. Remove "Send Directly to Loan Officer"
**Files to update:**
- templates/submit_application.html: Remove checkbox/option
- app.py submit_application(): Remove logic for needs_ci=0
- All applications must go through CI process

## Implementation Plan

### Phase 1: Display Text Changes (Quick)
1. Update all "Loan Staff" to "LPS" in templates
2. Update all "Reject" to "Disapprove" in templates
3. Update flash messages in app.py

### Phase 2: Decision Form Updates
1. Add "Defer" option to admin decision form
2. Update app.py to handle 'deferred' status
3. Test decision workflow

### Phase 3: CI Reassignment Feature
1. Add reassignment UI to admin application view
2. Create reassignment route in app.py
3. Update workload tracking
4. Add notifications

### Phase 4: Remove Direct to Loan Officer
1. Remove UI elements from submit form
2. Remove backend logic
3. Ensure all apps go through CI

## Quick Reference

### Status Values (Database)
- `submitted` - Initial state
- `assigned_to_ci` - Assigned to CI staff
- `ci_completed` - CI completed checklist
- `approved` - Loan officer approved
- `disapproved` - Loan officer disapproved (was 'rejected')
- `deferred` - Loan officer deferred decision (NEW)

### Role Values (Database - DO NOT CHANGE)
- `admin` - Super admin
- `loan_officer` - Loan officer
- `loan_staff` - LPS (display as "LPS")
- `ci_staff` - CI staff

### Display Names
- Admin → Admin
- Loan Officer → Loan Officer
- Loan Staff → LPS
- CI Staff → CI Staff
