# Quick Start Guide - New Features

## 🎯 Role Migration for Active Users

### What's New?
You can now change the role of active users directly from the Manage Users page!

### How to Use:
1. Login as **Admin** or **Loan Officer**
2. Go to **Manage Users** page
3. Scroll to **Active Users** section
4. Find the user you want to change
5. Click the **role dropdown** (shows current role)
6. Select new role (Admin, Loan Officer, LPS, or CI Staff)
7. Confirm in the dialog box
8. ✅ Success! Page reloads with updated role

### Example:
```
User: John Doe
Current Role: LPS
Action: Change to CI Staff
Result: John can now access CI Dashboard and perform CI tasks
```

---

## 📋 CI Workflow - Complete Process

### New Workflow:
```
1. CI Dashboard
   ↓ Click "Start"
   
2. Checkbox Summary Page
   ↓ Fill all checkboxes
   ↓ Click "Proceed to 5-Page Form"
   
3. 5-Page Wizard (Auto-filled!)
   ↓ Review auto-filled data
   ↓ Complete remaining fields
   ↓ Click "Submit"
   
4. Done! ✅
```

### What Gets Auto-Filled?
- ✅ All checkboxes from summary page (green highlight)
- ✅ OCR data from uploaded images (green highlight)
- ✅ Personal information
- ✅ Family background
- ✅ Address details
- ✅ Income and expenses
- ✅ Assets and liabilities

### How to Use:
1. Login as **CI Staff**
2. Go to **CI Dashboard**
3. Find application and click **"Start"**
4. Fill checkboxes in summary page
5. Click **"Proceed to 5-Page Form"**
6. Review auto-filled data (highlighted in green)
7. Complete remaining fields
8. Sign and submit

---

## 🤖 OCR Auto-Fill Feature

### What's New?
Upload images of DCCCO forms and AI will automatically extract and fill the data!

### How to Use:
1. Login as **LPS**
2. Go to **Submit Application** page
3. Fill basic information
4. Upload images of DCCCO forms (photos or scans)
5. Click **"Extract Data from Images (AI)"** button
6. Wait for processing (5-10 seconds)
7. ✅ Form fields auto-fill with extracted data
8. Review and correct any errors
9. Submit application

### Supported Forms:
- DCCCO Loan Application Form
- Personal Data Sheet
- Income Statement
- Family Background Form
- Any form with structured text

---

## 📝 LPS Can Edit Applications

### What's New?
LPS can now edit applications after submission!

### How to Use:
1. Login as **LPS**
2. Go to **Loan Dashboard**
3. Find submitted application
4. Click **"Edit"** button
5. Make changes (same form as create)
6. Click **"Update Application"**
7. ✅ Changes saved!

### When Can You Edit?
- Status: **Submitted** ✅
- Status: **Assigned to CI** ✅
- Status: **CI Completed** ❌ (locked)
- Status: **Approved/Disapproved** ❌ (locked)

---

## 📊 Loan Officer "In Process" Tab

### What's New?
Loan officers can now see all applications currently between LPS and CI!

### How to Use:
1. Login as **Loan Officer**
2. Go to **Admin Dashboard**
3. Click **"In Process"** tab (after Processed Applications)
4. View all applications with status:
   - Submitted (waiting for CI assignment)
   - Assigned to CI (CI is working on it)
5. Search by member name, contact, or address
6. Reassign CI staff if needed
7. Monitor progress

### Why Use This?
- Track applications in progress
- Reassign CI staff for better workload distribution
- Monitor CI completion times
- Identify bottlenecks

---

## 🔐 User Roles & Permissions

### Admin (Super Admin)
- ✅ Full system access
- ✅ Manage users (approve, deactivate, change roles)
- ✅ Manage loan types
- ✅ View all applications
- ✅ Approve/Disapprove/Defer applications
- ✅ System settings

### Loan Officer
- ✅ Manage users (approve, deactivate, change roles)
- ✅ View all applications
- ✅ Approve/Disapprove/Defer applications
- ✅ Assign CI staff
- ✅ View "In Process" tab
- ❌ System settings (admin only)

### LPS (Loan Staff)
- ✅ Submit loan applications
- ✅ Edit submitted applications (before CI completion)
- ✅ Upload documents
- ✅ Use OCR auto-fill
- ✅ View own applications
- ❌ Approve/Disapprove applications

### CI Staff
- ✅ View assigned applications
- ✅ Fill CI checklist (checkbox summary + 5-page wizard)
- ✅ Upload verification documents
- ✅ GPS tracking
- ✅ Digital signature
- ❌ Approve/Disapprove applications

---

## 🚀 Quick Tips

### For Admins/Loan Officers:
- Use "In Process" tab to monitor CI workload
- Reassign CI staff to balance workload
- Change user roles anytime (active users)
- Approve pending users and assign roles

### For LPS:
- Use OCR to save time on data entry
- Edit applications before CI completes them
- Upload clear images for better OCR accuracy
- Review OCR data before submitting

### For CI Staff:
- Start with checkbox summary (faster)
- Review auto-filled data in wizard
- Use GPS tracking for location verification
- Sign digitally before submitting

---

## 📞 Need Help?

### Common Questions:

**Q: Can I change an admin's role?**
A: No, admin roles cannot be changed for security.

**Q: What happens to CI route when I change role?**
A: If changing from CI Staff to another role, the route is automatically cleared.

**Q: Can I edit an approved application?**
A: No, only submitted and assigned_to_ci applications can be edited.

**Q: Does OCR work with handwritten forms?**
A: OCR works best with printed text. Handwritten text may have lower accuracy.

**Q: Can I skip the checkbox summary?**
A: No, the checkbox summary is required before the 5-page wizard.

---

## 🎉 What's Next?

1. **Deploy to Production** - Push changes to Render
2. **Test All Features** - Verify everything works
3. **Train Users** - Show them the new features
4. **Monitor Usage** - Check logs for errors
5. **Gather Feedback** - Improve based on user input

---

**Version:** 2.0
**Date:** 2026-04-19
**Status:** Ready to Use
