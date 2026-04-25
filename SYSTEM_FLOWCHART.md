# DCCCO Loan Management System - Complete Workflow Flowchart

## System Overview

This document provides a comprehensive flowchart of the DCCCO Multipurpose Cooperative Loan Management System, showing the complete workflow for all user roles and their interactions with the database.

---

## 1. SUPER ADMIN WORKFLOW

### Login & Dashboard Access
```
START
  ↓
Login (admin@dccco.test / admin123)
  ↓
Authenticate against users table
  ↓
Admin Dashboard
  ↓
[Main Menu - Select Action]
```

### A. View All Applications
```
View All Applications
  ↓
Query: SELECT * FROM loan_applications
  ↓
Filter by Status:
  - Submitted
  - Assigned to CI
  - CI Completed
  - Approved
  - Disapproved
  - Deferred
  ↓
Display Applications List
  ↓
Back to Dashboard
```

### B. Review & Decide on Application
```
Review Application
  ↓
Query: SELECT la.*, u.name as ci_staff_name 
       FROM loan_applications la
       LEFT JOIN users u ON la.assigned_ci_staff = u.id
       WHERE la.id = ?
  ↓

Display Application Details:
  - Member Information (name, contact, address)
  - Loan Details (amount, type, purpose)
  - LPS Remarks
  - CI Checklist (3 pages of investigation data)
  - Documents (uploaded files)
  - GPS Location (ci_latitude, ci_longitude)
  ↓
[Decision Point: Make Decision]
  ↓
  ├─→ APPROVE
  │     ↓
  │   Add Admin Notes
  │     ↓
  │   UPDATE loan_applications 
  │   SET status='approved', 
  │       admin_notes=?, 
  │       admin_decision_at=NOW()
  │   WHERE id=?
  │     ↓
  │   Send SMS to Applicant (via Semaphore API)
  │     ↓
  │   INSERT INTO notifications (user_id, message, link)
  │     ↓
  │   Emit Socket.IO event (real-time update)
  │     ↓
  │   Back to Dashboard
  │
  ├─→ DISAPPROVE
  │     ↓
  │   Add Reason for Disapproval
  │     ↓
  │   UPDATE loan_applications 
  │   SET status='disapproved', 
  │       admin_notes=?, 
  │       admin_decision_at=NOW()
  │   WHERE id=?
  │     ↓
  │   Send SMS to Applicant
  │     ↓
  │   INSERT INTO notifications
  │     ↓
  │   Emit Socket.IO event
  │     ↓
  │   Back to Dashboard
  │
  └─→ DEFER
        ↓
      Add Reason for Deferral
        ↓

      UPDATE loan_applications 
      SET status='deferred', 
          admin_notes=?, 
          admin_decision_at=NOW()
      WHERE id=?
        ↓
      Send SMS to Applicant
        ↓
      INSERT INTO notifications
        ↓
      Emit Socket.IO event
        ↓
      Back to Dashboard
```

### C. Manage Users
```
Manage Users
  ↓
Query: SELECT * FROM users ORDER BY created_at DESC
  ↓
Display User List with Status:
  - Approved Users
  - Pending Approval
  ↓
[User Action Menu]
  ↓
  ├─→ Approve New User
  │     ↓
  │   UPDATE users SET is_approved=1 WHERE id=?
  │     ↓
  │   INSERT INTO notifications (user_id, message)
  │     ↓
  │   Back to User List
  │
  ├─→ Assign Role
  │     ↓
  │   UPDATE users SET role=? WHERE id=?
  │   (Roles: admin, loan_officer, loan_staff, ci_staff)
  │     ↓
  │   Back to User List
  │
  ├─→ Assign CI Route
  │     ↓
  │   UPDATE users SET assigned_route=? WHERE id=?
  │   (Routes: route_1_bayawan_kalumboyan, route_2_bayawan_basay, etc.)
  │     ↓
  │   Back to User List
  │
  └─→ Set Permissions (for Loan Officers)
        ↓
      UPDATE users SET permissions=? WHERE id=?
      (Permissions: view_reports, manage_users, ci_tracking)
        ↓
      Back to User List
```


### D. System Settings
```
System Settings
  ↓
Query: SELECT * FROM system_settings
  ↓
Display Settings:
  - company_name
  - max_loan_amount
  - min_loan_amount
  - default_interest_rate
  - ci_required_threshold
  ↓
Update Settings
  ↓
UPDATE system_settings SET setting_value=? WHERE setting_key=?
  ↓
Save Changes
  ↓
Back to Dashboard
```

### E. Manage Loan Types
```
Manage Loan Types
  ↓
Query: SELECT * FROM loan_types ORDER BY loan_name
  ↓
Display Loan Types (18 types):
  - Agricultural with Chattel
  - Agricultural with REM
  - Business with Chattel
  - Multipurpose loans
  - Salary loans
  - Car loans
  - etc.
  ↓
[Loan Type Action Menu]
  ↓
  ├─→ Add New Loan Type
  │     ↓
  │   INSERT INTO loan_types (loan_name, description, is_active)
  │   VALUES (?, ?, 1)
  │     ↓
  │   Back to Loan Types List
  │
  ├─→ Edit Loan Type
  │     ↓
  │   UPDATE loan_types SET loan_name=?, description=? WHERE id=?
  │     ↓
  │   Back to Loan Types List
  │
  ├─→ Activate/Deactivate
  │     ↓
  │   UPDATE loan_types SET is_active=? WHERE id=?
  │     ↓
  │   Back to Loan Types List
  │
  └─→ Delete Loan Type
        ↓

      DELETE FROM loan_types WHERE id=?
        ↓
      Back to Loan Types List
```

### F. Reports & Analytics
```
Reports
  ↓
Query Database:
  - SELECT COUNT(*) FROM loan_applications WHERE status='approved'
  - SELECT COUNT(*) FROM loan_applications WHERE status='disapproved'
  - SELECT SUM(loan_amount) FROM loan_applications WHERE status='approved'
  - SELECT * FROM loan_applications WHERE submitted_at BETWEEN ? AND ?
  ↓
Generate Report:
  - Applications by Status
  - Applications by Date Range
  - Applications by CI Staff
  - Approval Rate
  - Total Loan Amount Approved
  ↓
Export Options:
  - Excel (XLSX)
  - PDF
  - CSV
  ↓
Download Report
  ↓
Back to Dashboard
```

### G. CI Tracking (Real-time GPS)
```
CI Tracking
  ↓
Query: SELECT lt.*, u.name, u.profile_photo
       FROM location_tracking lt
       JOIN users u ON lt.user_id = u.id
       WHERE u.role='ci_staff'
       ORDER BY lt.tracked_at DESC
  ↓
Display CI Staff Locations on Map:
  - Real-time GPS coordinates
  - Activity status
  - Last seen timestamp
  - Current assignment
  ↓
Auto-refresh every 30 seconds (Socket.IO)
  ↓
Back to Dashboard
```

### H. Messaging System
```
Messages
  ↓
Query: SELECT dm.*, u.name as sender_name
       FROM direct_messages dm
       JOIN users u ON dm.sender_id = u.id
       WHERE dm.receiver_id=? OR dm.sender_id=?
       ORDER BY dm.sent_at DESC
  ↓

Display Message Threads
  ↓
[Message Actions]
  ↓
  ├─→ Send New Message
  │     ↓
  │   INSERT INTO direct_messages 
  │   (sender_id, receiver_id, message, sent_at)
  │   VALUES (?, ?, ?, NOW())
  │     ↓
  │   Emit Socket.IO event (real-time delivery)
  │     ↓
  │   INSERT INTO notifications (user_id, message)
  │     ↓
  │   Back to Messages
  │
  ├─→ Mark as Read
  │     ↓
  │   UPDATE direct_messages SET is_read=1 WHERE id=?
  │     ↓
  │   Back to Messages
  │
  └─→ Delete Message
        ↓
      UPDATE direct_messages SET is_deleted=1 WHERE id=?
        ↓
      Back to Messages
```

---

## 2. LOAN OFFICER WORKFLOW

### Login & Dashboard Access
```
START
  ↓
Login (admin@dccco.test / admin123)
  ↓
Authenticate against users table
  ↓
Loan Officer Dashboard
  ↓
[Main Menu - Select Action]
```

### A. View Applications for Review
```
View Applications
  ↓
Query: SELECT la.*, u1.name as loan_staff_name, u2.name as ci_staff_name
       FROM loan_applications la
       LEFT JOIN users u1 ON la.submitted_by = u1.id
       LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
       WHERE la.status IN ('ci_completed', 'submitted')
       ORDER BY la.submitted_at ASC
  ↓
Display Applications List
  ↓
Back to Dashboard
```


### B. Review & Make Decision
```
Review Application
  ↓
Query: SELECT * FROM loan_applications WHERE id=?
  ↓
Display:
  - Member Details
  - Loan Details
  - LPS Remarks
  - CI Checklist (if completed)
  - Documents
  ↓
[Decision Point]
  ↓
  ├─→ APPROVE
  │     ↓
  │   UPDATE loan_applications 
  │   SET status='approved', admin_notes=?, admin_decision_at=NOW()
  │   WHERE id=?
  │     ↓
  │   Send SMS to Applicant
  │     ↓
  │   INSERT INTO notifications
  │     ↓
  │   Back to Dashboard
  │
  ├─→ DISAPPROVE
  │     ↓
  │   UPDATE loan_applications 
  │   SET status='disapproved', admin_notes=?, admin_decision_at=NOW()
  │   WHERE id=?
  │     ↓
  │   Send SMS to Applicant
  │     ↓
  │   Back to Dashboard
  │
  └─→ DEFER
        ↓
      UPDATE loan_applications 
      SET status='deferred', admin_notes=?, admin_decision_at=NOW()
      WHERE id=?
        ↓
      Send SMS to Applicant
        ↓
      Back to Dashboard
```

### C. CI Tracking (If Permission Granted)
```
CI Tracking
  ↓
Check Permission: SELECT permissions FROM users WHERE id=?
  ↓
IF 'ci_tracking' IN permissions:
  ↓
  Query: SELECT * FROM location_tracking WHERE user_id IN 
         (SELECT id FROM users WHERE role='ci_staff')
  ↓
  Display CI Staff Locations on Map
  ↓
  Back to Dashboard
ELSE:
  ↓
  Access Denied
```


### D. Reports (If Permission Granted)
```
Reports
  ↓
Check Permission: SELECT permissions FROM users WHERE id=?
  ↓
IF 'view_reports' IN permissions:
  ↓
  Query: SELECT * FROM loan_applications
  ↓
  Generate Reports
  ↓
  Export to Excel/PDF
  ↓
  Back to Dashboard
ELSE:
  ↓
  Access Denied
```

### E. Messages
```
Messages
  ↓
Query: SELECT * FROM direct_messages 
       WHERE receiver_id=? OR sender_id=?
  ↓
Send/Receive Messages (Real-time via Socket.IO)
  ↓
UPDATE direct_messages SET is_read=1 WHERE id=?
  ↓
Back to Dashboard
```

---

## 3. LPS STAFF (LOAN PROCESSING STAFF) WORKFLOW

### Login & Dashboard Access
```
START
  ↓
Login (loan@dccco.test / loan123)
  ↓
Authenticate against users table
  ↓
LPS Dashboard
  ↓
[Main Menu - Select Action]
```

### A. Submit New Loan Application

#### Step 1: Enter Member Information
```
Submit New Application
  ↓
Step 1: Member Information
  ↓
Input Fields:
  - Member Name (with autocomplete from previous applications)
  - Contact Number (Philippine format: 09XX-XXX-XXXX)
  - Address (with barangay/municipality dropdown)
  - Date of Birth
  ↓
Query for Autocomplete:
  SELECT DISTINCT member_name, member_contact, member_address
  FROM loan_applications
  WHERE member_name LIKE ?
  ↓
Next Step
```


#### Step 2: Enter Loan Details
```
Step 2: Loan Details
  ↓
Query: SELECT * FROM loan_types WHERE is_active=1
  ↓
Input Fields:
  - Loan Type (dropdown from 18 types)
  - Loan Amount (₱5,000 - ₱500,000)
  - Loan Purpose
  - Loan Terms (months)
  - Payment Mode
  ↓
Next Step
```

#### Step 3: Add LPS Remarks
```
Step 3: LPS Remarks
  ↓
Input Fields:
  - Initial Assessment
  - Recommendations
  - Risk Factors
  - Special Notes
  ↓
Next Step
```

#### Step 4: Upload Documents
```
Step 4: Upload Documents
  ↓
Upload Files:
  - Valid ID (front & back)
  - Income Proof (payslip, ITR, business permit)
  - Collateral Documents (if applicable)
  - Other Supporting Documents
  ↓
Validate File Types: PNG, JPG, PDF, DOC, DOCX
  ↓
Save Files to Server (uploads folder)
  ↓
Generate Unique Filenames: {app_id}_{uuid}_{filename}
  ↓
Next Step
```

#### Step 5: Submit Application
```
Submit Application
  ↓
Check for Duplicate:
  SELECT id FROM loan_applications 
  WHERE LOWER(member_name) = LOWER(?)
  AND status NOT IN ('disapproved', 'approved')
  ↓
IF Duplicate Found:
  ↓
  Display Warning: "Active application already exists"
  ↓
  Back to Form
ELSE:
  ↓
  INSERT INTO loan_applications
  (member_name, member_contact, member_address, loan_amount, 
   loan_type, lps_remarks, needs_ci_interview, submitted_by, 
   status, submitted_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', NOW())
  ↓

  Get Application ID (lastrowid)
  ↓
  INSERT INTO documents
  (loan_application_id, file_name, file_path, uploaded_by, uploaded_at)
  VALUES (?, ?, ?, ?, NOW())
  FOR EACH uploaded file
  ↓
  [SYSTEM AUTO-ASSIGNMENT PROCESS]
  ↓
  IF needs_ci_interview = 1:
    ↓
    Parse member_address to find matching route
    ↓
    Route Matching Logic:
      - route_1_bayawan_kalumboyan: Kalumboyan, Kalamtukan, Malabugas, etc.
      - route_2_bayawan_basay: Basay, Actin, Bal-os, etc.
      - route_3_bayawan_sipalay: Sipalay, Cabadiangan, etc.
      - route_4_bayawan_santa_catalina: Santa Catalina, Alangilan, etc.
      - route_5_bayawan_center: Ali-is, Banaybanay, Poblacion, etc.
      - route_6_bayawan_omod: Omod, Tamisu
    ↓
    Query: SELECT id FROM users 
           WHERE role='ci_staff' 
           AND is_approved=1
           AND assigned_route LIKE '%{matched_route}%'
           LIMIT 1
    ↓
    IF Route Match Found:
      ↓
      Assign to Route-matched CI Staff
    ELSE:
      ↓
      Fallback to Workload-based Assignment:
      ↓
      Query: SELECT id FROM users 
             WHERE role='ci_staff' 
             AND is_approved=1
             ORDER BY current_workload ASC
             LIMIT 1
      ↓
      Assign to CI Staff with Lowest Workload
    ↓
    UPDATE loan_applications 
    SET status='assigned_to_ci', assigned_ci_staff=?
    WHERE id=?
    ↓
    UPDATE users 
    SET current_workload = current_workload + 1
    WHERE id=?
    ↓
    INSERT INTO notifications
    (user_id, message, link, created_at)
    VALUES (?, 'New loan application assigned: {member_name}', 
            '/ci/application/{app_id}', NOW())
    ↓
    Emit Socket.IO event: 'new_application'
  ELSE:
    ↓
    Send directly to Loan Officer
    ↓
    Query: SELECT id FROM users WHERE role='loan_officer' LIMIT 1
    ↓
    INSERT INTO notifications
    (user_id, message, link, created_at)
    VALUES (?, 'New loan application submitted: {member_name}',
            '/admin/application/{app_id}', NOW())
  ↓
  Display Success Message
  ↓
  Back to Dashboard
```


### B. View My Applications
```
View My Applications
  ↓
Query: SELECT la.*, u.name as ci_staff_name
       FROM loan_applications la
       LEFT JOIN users u ON la.assigned_ci_staff = u.id
       WHERE la.submitted_by = ?
       ORDER BY la.submitted_at DESC
  ↓
Display Applications with Status:
  - Submitted (yellow)
  - Assigned to CI (blue)
  - CI Completed (purple)
  - Approved (green)
  - Disapproved (red)
  - Deferred (orange)
  ↓
Back to Dashboard
```

### C. Track Application Status
```
Track Application Status
  ↓
Query: SELECT la.*, u1.name as ci_staff_name, u2.name as loan_officer_name
       FROM loan_applications la
       LEFT JOIN users u1 ON la.assigned_ci_staff = u1.id
       LEFT JOIN users u2 ON la.admin_decision_at IS NOT NULL
       WHERE la.id = ?
  ↓
Display Timeline:
  - Submitted: {submitted_at}
  - Assigned to CI: {assigned_at}
  - CI Completed: {ci_completed_at}
  - Admin Decision: {admin_decision_at}
  ↓
Display Current Status & Notes
  ↓
Back to Dashboard
```

### D. Messages
```
Messages
  ↓
Query: SELECT dm.*, u.name as sender_name
       FROM direct_messages dm
       JOIN users u ON dm.sender_id = u.id
       WHERE dm.receiver_id = ?
       ORDER BY dm.sent_at DESC
  ↓
Send/Receive Messages (Real-time via Socket.IO)
  ↓
UPDATE direct_messages SET is_read=1 WHERE id=?
  ↓
Back to Dashboard
```

---

## 4. CI/BI STAFF (CREDIT INVESTIGATION) WORKFLOW

### Login & Dashboard Access
```
START
  ↓
Login (ci@dccco.test / ci123)
  ↓
Authenticate against users table
  ↓
CI Dashboard
  ↓
[Main Menu - Select Action]
```


### A. View Assigned Applications
```
View Assigned Applications
  ↓
Query: SELECT la.*, u.name as loan_staff_name
       FROM loan_applications la
       LEFT JOIN users u ON la.submitted_by = u.id
       WHERE la.assigned_ci_staff = ?
       AND la.status = 'assigned_to_ci'
       ORDER BY la.submitted_at ASC
  ↓
Display Applications List with Priority
  ↓
Back to Dashboard
```

### B. Conduct Credit Investigation

#### Step 1: Review Application
```
Conduct Investigation
  ↓
Step 1: Review Application
  ↓
Query: SELECT la.*, u.name as loan_staff_name
       FROM loan_applications la
       LEFT JOIN users u ON la.submitted_by = u.id
       WHERE la.id = ? AND la.assigned_ci_staff = ?
  ↓
Display:
  - Member Details (name, contact, address)
  - Loan Details (amount, type, purpose)
  - LPS Remarks
  - Uploaded Documents
  ↓
Query: SELECT * FROM documents 
       WHERE loan_application_id = ?
       ORDER BY uploaded_at DESC
  ↓
View/Download Documents
  ↓
Next Step
```

#### Step 2: Field Investigation
```
Step 2: Field Investigation
  ↓
Auto-capture GPS Location (using browser geolocation API)
  ↓
INSERT INTO location_tracking
(user_id, latitude, longitude, activity, tracked_at)
VALUES (?, ?, ?, 'Field Investigation', NOW())
  ↓
Take Photos:
  - Property/Collateral Photos
  - Interview Photos
  - Supporting Evidence
  ↓
Save Photos to Server (uploads folder)
  ↓
Generate Unique Filenames: {app_id}_interview_{uuid}_{filename}
  ↓
Next Step
```


#### Step 3: Complete CI Checklist (3 Pages)

##### Page 1: Personal Information
```
Step 3: CI Checklist
  ↓
PAGE 1: Personal Information
  ↓
Input Fields:
  - Family Background:
    • Spouse Name
    • Number of Children
    • Dependents
    • Family Income
  - Employment:
    • Employer Name
    • Position
    • Years of Service
    • Monthly Income
    • Employment Status
  - Monthly Expenses:
    • Food & Utilities
    • Education
    • Transportation
    • Loan Payments
    • Other Expenses
  - Assets:
    • Real Estate Properties
    • Vehicles
    • Savings/Investments
    • Other Assets
  ↓
Next Page
```

##### Page 2: Credit History
```
PAGE 2: Credit History
  ↓
Input Fields:
  - Previous Loans:
    • Loan Provider
    • Loan Amount
    • Payment Status
    • Outstanding Balance
  - Payment History:
    • On-time Payments
    • Late Payments
    • Defaults
  - Credit Score Assessment:
    • Excellent (750+)
    • Good (650-749)
    • Fair (550-649)
    • Poor (<550)
  - Character References:
    • Reference 1 (Name, Contact, Relationship)
    • Reference 2 (Name, Contact, Relationship)
    • Reference 3 (Name, Contact, Relationship)
  - Verification:
    • References Contacted (Yes/No)
    • Feedback Summary
  ↓
Next Page
```


##### Page 3: Property/Collateral Assessment
```
PAGE 3: Property/Collateral
  ↓
Input Fields:
  - Property Description:
    • Property Type (House, Land, Vehicle, etc.)
    • Location/Address
    • Size/Area
    • Condition
  - Property Value:
    • Market Value
    • Assessed Value
    • Appraised Value
  - Ownership Documents:
    • Title/Deed
    • Tax Declaration
    • Registration Papers
  - Photos:
    • Property Photos (uploaded)
    • Document Photos (uploaded)
  - Collateral Assessment:
    • Sufficient (Yes/No)
    • Marketability (High/Medium/Low)
    • Legal Issues (None/Pending/Resolved)
  ↓
Convert All Checklist Data to JSON Format:
  {
    "personal_info": {...},
    "credit_history": {...},
    "property_collateral": {...}
  }
  ↓
Next Step
```

#### Step 4: Add CI Notes & Recommendation
```
Step 4: CI Notes
  ↓
Input Fields:
  - Investigation Findings (detailed summary)
  - Risk Assessment:
    • Low Risk
    • Medium Risk
    • High Risk
  - Recommendation:
    • Strongly Recommend Approval
    • Recommend Approval
    • Recommend with Conditions
    • Do Not Recommend
  - Special Notes/Concerns
  ↓
Next Step
```

#### Step 5: Digital Signature
```
Step 5: Digital Signature
  ↓
Capture Signature:
  - Use signature pad (canvas)
  - Or use registered signature from profile
  ↓
Save Signature to Server (signatures folder)
  ↓
Generate Unique Filename: ci_signature_{user_id}_{uuid}.png
  ↓
Next Step
```


#### Step 6: Submit Investigation
```
Submit Investigation
  ↓
UPDATE loan_applications
SET status = 'ci_completed',
    ci_checklist_data = ?,  -- JSON data
    ci_notes = ?,
    ci_signature = ?,
    ci_latitude = ?,
    ci_longitude = ?,
    ci_completed_at = NOW()
WHERE id = ?
  ↓
INSERT INTO documents
(loan_application_id, file_name, file_path, uploaded_by, uploaded_at)
VALUES (?, ?, ?, ?, NOW())
FOR EACH interview photo
  ↓
UPDATE users
SET current_workload = current_workload - 1
WHERE id = ?
  ↓
Query: SELECT id FROM users WHERE role='loan_officer' LIMIT 1
  ↓
INSERT INTO notifications
(user_id, message, link, created_at)
VALUES (?, 'CI interview completed for: {member_name}',
        '/admin/application/{app_id}', NOW())
  ↓
INSERT INTO notifications
(user_id, message, link, created_at)
VALUES ({lps_staff_id}, 'CI completed for application: {member_name}',
        '/loan/dashboard', NOW())
  ↓
Emit Socket.IO event: 'application_updated'
  ↓
Display Success Message
  ↓
Back to Dashboard
```

### C. View Investigation History
```
View Investigation History
  ↓
Query: SELECT la.*, u.name as loan_staff_name
       FROM loan_applications la
       LEFT JOIN users u ON la.submitted_by = u.id
       WHERE la.assigned_ci_staff = ?
       AND la.status = 'ci_completed'
       ORDER BY la.ci_completed_at DESC
  ↓
Display Completed Investigations
  ↓
Back to Dashboard
```


### D. GPS Location Tracking
```
GPS Location Tracking
  ↓
Auto-track Location during Field Work
  ↓
Browser Geolocation API:
  navigator.geolocation.getCurrentPosition()
  ↓
INSERT INTO location_tracking
(user_id, latitude, longitude, activity, tracked_at)
VALUES (?, ?, ?, 'Field Work', NOW())
EVERY 5 MINUTES
  ↓
Display on Map (for Admin/Loan Officer)
  ↓
Query: SELECT * FROM location_tracking 
       WHERE user_id = ?
       ORDER BY tracked_at DESC
       LIMIT 1
  ↓
Show Current Location on Dashboard
  ↓
Back to Dashboard
```

### E. Messages
```
Messages
  ↓
Query: SELECT dm.*, u.name as sender_name
       FROM direct_messages dm
       JOIN users u ON dm.sender_id = u.id
       WHERE dm.receiver_id = ?
       ORDER BY dm.sent_at DESC
  ↓
Send/Receive Messages (Real-time via Socket.IO)
  ↓
UPDATE direct_messages SET is_read=1 WHERE id=?
  ↓
Back to Dashboard
```

---

## 5. COMPLETE SYSTEM DATA FLOW DIAGRAM

### Database Tables & Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATABASE SCHEMA                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  users                                                           │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ email (UNIQUE)                                              │
│  ├─ password_hash                                               │
│  ├─ name                                                        │
│  ├─ role (admin, loan_officer, loan_staff, ci_staff)           │
│  ├─ is_approved (0 or 1)                                        │
│  ├─ current_workload (INTEGER)                                  │
│  ├─ assigned_route (TEXT)                                       │
│  ├─ permissions (TEXT)                                          │
│  ├─ signature_path                                              │
│  ├─ backup_email                                                │
│  ├─ profile_photo                                               │
│  ├─ is_online (0 or 1)                                          │
│  └─ last_seen (TIMESTAMP)                                       │
│                                                                  │

│  loan_applications                                               │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ member_name                                                 │
│  ├─ member_contact                                              │
│  ├─ member_address                                              │
│  ├─ loan_amount (DECIMAL)                                       │
│  ├─ loan_type                                                   │
│  ├─ status (submitted, assigned_to_ci, ci_completed,           │
│  │           approved, disapproved, deferred)                   │
│  ├─ needs_ci_interview (0 or 1)                                 │
│  ├─ submitted_by (FOREIGN KEY → users.id)                      │
│  ├─ assigned_ci_staff (FOREIGN KEY → users.id)                 │
│  ├─ lps_remarks (TEXT)                                          │
│  ├─ ci_notes (TEXT)                                             │
│  ├─ ci_checklist_data (JSON)                                    │
│  ├─ ci_signature (TEXT)                                         │
│  ├─ ci_latitude (DECIMAL)                                       │
│  ├─ ci_longitude (DECIMAL)                                      │
│  ├─ ci_completed_at (TIMESTAMP)                                 │
│  ├─ admin_notes (TEXT)                                          │
│  ├─ admin_decision_at (TIMESTAMP)                               │
│  └─ submitted_at (TIMESTAMP)                                    │
│                                                                  │
│  documents                                                       │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ loan_application_id (FOREIGN KEY → loan_applications.id)   │
│  ├─ file_name                                                   │
│  ├─ file_path                                                   │
│  ├─ uploaded_by (FOREIGN KEY → users.id)                       │
│  └─ uploaded_at (TIMESTAMP)                                     │
│                                                                  │
│  direct_messages                                                 │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ sender_id (FOREIGN KEY → users.id)                         │
│  ├─ receiver_id (FOREIGN KEY → users.id)                       │
│  ├─ message (TEXT)                                              │
│  ├─ sent_at (TIMESTAMP)                                         │
│  ├─ is_read (0 or 1)                                            │
│  ├─ is_edited (0 or 1)                                          │
│  └─ is_deleted (0 or 1)                                         │
│                                                                  │
│  notifications                                                   │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ user_id (FOREIGN KEY → users.id)                           │
│  ├─ message (TEXT)                                              │
│  ├─ link (TEXT)                                                 │
│  ├─ is_read (0 or 1)                                            │
│  └─ created_at (TIMESTAMP)                                      │
│                                                                  │
│  location_tracking                                               │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ user_id (FOREIGN KEY → users.id)                           │
│  ├─ latitude (DECIMAL)                                          │
│  ├─ longitude (DECIMAL)                                         │
│  ├─ activity (TEXT)                                             │
│  └─ tracked_at (TIMESTAMP)                                      │
│                                                                  │

│  loan_types                                                      │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ loan_name                                                   │
│  ├─ description                                                 │
│  └─ is_active (0 or 1)                                          │
│                                                                  │
│  system_settings                                                 │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ setting_key (UNIQUE)                                        │
│  ├─ setting_value                                               │
│  └─ description                                                 │
│                                                                  │
│  sms_templates                                                   │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ template_name                                               │
│  ├─ template_content                                            │
│  └─ is_active (0 or 1)                                          │
│                                                                  │
│  password_reset_codes                                            │
│  ├─ id (PRIMARY KEY)                                            │
│  ├─ user_id (FOREIGN KEY → users.id)                           │
│  ├─ code (6-digit)                                              │
│  ├─ expires_at (TIMESTAMP)                                      │
│  └─ created_at (TIMESTAMP)                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Complete Application Lifecycle Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                  LOAN APPLICATION LIFECYCLE                       │
└──────────────────────────────────────────────────────────────────┘

1. LPS STAFF SUBMITS APPLICATION
   ↓
   INSERT INTO loan_applications
   (member_name, contact, address, amount, type, lps_remarks, 
    submitted_by, status='submitted', submitted_at=NOW())
   ↓
   INSERT INTO documents (for each uploaded file)
   ↓

2. SYSTEM AUTO-ASSIGNMENT
   ↓
   IF needs_ci_interview = 1:
     ↓
     Route-based Assignment:
       - Parse member_address
       - Match to CI route (route_1 to route_6)
       - SELECT id FROM users WHERE assigned_route LIKE '%{route}%'
     ↓
     Fallback to Workload-based:
       - SELECT id FROM users WHERE role='ci_staff' 
         ORDER BY current_workload ASC LIMIT 1
     ↓
     UPDATE loan_applications 
     SET status='assigned_to_ci', assigned_ci_staff=?
     ↓
     UPDATE users SET current_workload = current_workload + 1
     ↓
     INSERT INTO notifications (for CI staff)
     ↓
     Emit Socket.IO: 'new_application'
   ↓


3. CI STAFF CONDUCTS INVESTIGATION
   ↓
   INSERT INTO location_tracking (GPS coordinates)
   ↓
   Complete 3-page CI Checklist (JSON format)
   ↓
   Upload interview photos
   ↓
   INSERT INTO documents (interview photos)
   ↓
   Capture digital signature
   ↓
   UPDATE loan_applications
   SET status='ci_completed',
       ci_checklist_data=?,
       ci_notes=?,
       ci_signature=?,
       ci_latitude=?,
       ci_longitude=?,
       ci_completed_at=NOW()
   ↓
   UPDATE users SET current_workload = current_workload - 1
   ↓
   INSERT INTO notifications (for Loan Officer & LPS)
   ↓
   Emit Socket.IO: 'application_updated'
   ↓

4. LOAN OFFICER/ADMIN REVIEWS
   ↓
   SELECT la.*, u1.name as loan_staff_name, u2.name as ci_staff_name
   FROM loan_applications la
   LEFT JOIN users u1 ON la.submitted_by = u1.id
   LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
   WHERE la.status = 'ci_completed'
   ↓
   Review:
     - Member details
     - Loan details
     - LPS remarks
     - CI checklist (3 pages)
     - Documents
     - GPS location
   ↓
   [DECISION POINT]
   ↓
   ├─→ APPROVE
   │     ↓
   │   UPDATE loan_applications
   │   SET status='approved', admin_notes=?, admin_decision_at=NOW()
   │     ↓
   │   Send SMS to Applicant (Semaphore API)
   │     ↓
   │   INSERT INTO notifications (for LPS & CI)
   │     ↓
   │   Emit Socket.IO: 'application_updated'
   │
   ├─→ DISAPPROVE
   │     ↓
   │   UPDATE loan_applications
   │   SET status='disapproved', admin_notes=?, admin_decision_at=NOW()
   │     ↓
   │   Send SMS to Applicant
   │     ↓
   │   INSERT INTO notifications
   │     ↓
   │   Emit Socket.IO: 'application_updated'
   │
   └─→ DEFER
         ↓
       UPDATE loan_applications
       SET status='deferred', admin_notes=?, admin_decision_at=NOW()
         ↓
       Send SMS to Applicant
         ↓
       INSERT INTO notifications
         ↓
       Emit Socket.IO: 'application_updated'
   ↓

5. ALL USERS NOTIFIED
   ↓
   Real-time notifications via Socket.IO
   ↓
   SMS sent to applicant
   ↓
   Dashboard updates automatically
   ↓
   END
```



---

## 6. REAL-TIME FEATURES (SOCKET.IO)

### A. Real-time Messaging
```
User A sends message to User B
  ↓
INSERT INTO direct_messages
(sender_id, receiver_id, message, sent_at)
VALUES (?, ?, ?, NOW())
  ↓
Emit Socket.IO event: 'new_message'
  ↓
User B receives message instantly (if online)
  ↓
UPDATE direct_messages SET is_read=1 WHERE id=?
  ↓
Emit Socket.IO event: 'message_read'
  ↓
User A sees "Read" status instantly
```

### B. Real-time Notifications
```
System creates notification
  ↓
INSERT INTO notifications
(user_id, message, link, created_at)
VALUES (?, ?, ?, NOW())
  ↓
Emit Socket.IO event: 'new_notification'
  ↓
User receives notification instantly (if online)
  ↓
Browser shows notification badge
  ↓
User clicks notification
  ↓
UPDATE notifications SET is_read=1 WHERE id=?
  ↓
Redirect to link
```

### C. Real-time Dashboard Updates
```
Application status changes
  ↓
UPDATE loan_applications SET status=? WHERE id=?
  ↓
Emit Socket.IO event: 'application_updated'
  ↓
All connected dashboards update instantly:
  - LPS Dashboard
  - CI Dashboard
  - Admin Dashboard
  ↓
No page refresh needed
```

### D. Real-time GPS Tracking
```
CI Staff in field
  ↓
Browser captures GPS coordinates every 5 minutes
  ↓
INSERT INTO location_tracking
(user_id, latitude, longitude, activity, tracked_at)
VALUES (?, ?, ?, 'Field Work', NOW())
  ↓
Emit Socket.IO event: 'location_update'
  ↓
Admin/Loan Officer sees updated location on map instantly
  ↓
No page refresh needed
```



---

## 7. EXTERNAL SERVICES INTEGRATION

### A. SMS Notifications (Semaphore API)
```
Application Decision Made
  ↓
Prepare SMS Message:
  - Approved: "Congratulations! Your loan application has been approved..."
  - Disapproved: "We regret to inform you that your loan application..."
  - Deferred: "Your loan application requires additional review..."
  ↓
Call Semaphore API:
  POST https://api.semaphore.co/api/v4/messages
  Headers: Authorization: {SEMAPHORE_API_KEY}
  Body: {
    "apikey": "{SEMAPHORE_API_KEY}",
    "number": "{member_contact}",
    "message": "{message_content}",
    "sendername": "DCCCO"
  }
  ↓
IF Success:
  ↓
  Log SMS sent
  ↓
  Display success message
ELSE:
  ↓
  Log error
  ↓
  Display error message (but don't block application)
```

### B. Email Notifications (Resend API)
```
Password Reset Request
  ↓
Generate 6-digit verification code
  ↓
INSERT INTO password_reset_codes
(user_id, code, expires_at, created_at)
VALUES (?, ?, NOW() + 15 minutes, NOW())
  ↓
Call Resend API:
  POST https://api.resend.com/emails
  Headers: Authorization: Bearer {RESEND_API_KEY}
  Body: {
    "from": "noreply@dccco.com",
    "to": "{user_email}",
    "subject": "Password Reset Verification Code",
    "html": "{email_template_with_code}"
  }
  ↓
IF Success:
  ↓
  Display "Check your email" message
ELSE:
  ↓
  Display error message
```

### C. File Storage (Server)
```
User uploads file
  ↓
Validate file type: PNG, JPG, PDF, DOC, DOCX
  ↓
Validate file size: Max 16MB
  ↓
Sanitize filename: Remove special characters
  ↓
Generate unique filename: {app_id}_{uuid}_{filename}
  ↓
Save to server: uploads/{unique_filename}
  ↓
INSERT INTO documents
(loan_application_id, file_name, file_path, uploaded_by, uploaded_at)
VALUES (?, ?, ?, ?, NOW())
  ↓
Return file URL: /uploads/{unique_filename}
```



---

## 8. SECURITY & AUTHENTICATION

### A. User Login Flow
```
User enters email & password
  ↓
Query: SELECT * FROM users WHERE email=?
  ↓
IF User Found:
  ↓
  Verify password: check_password_hash(stored_hash, entered_password)
  ↓
  IF Password Correct:
    ↓
    Check approval status: is_approved = 1?
    ↓
    IF Approved:
      ↓
      Create session
      ↓
      UPDATE users SET is_online=1, last_seen=NOW() WHERE id=?
      ↓
      Redirect to role-based dashboard:
        - admin/loan_officer → /admin/dashboard
        - loan_staff → /loan/dashboard
        - ci_staff → /ci/dashboard
    ELSE:
      ↓
      Display: "Account pending approval"
  ELSE:
    ↓
    Display: "Invalid credentials"
ELSE:
  ↓
  Display: "Invalid credentials"
```

### B. Password Reset Flow
```
User clicks "Forgot Password"
  ↓
Enter email address
  ↓
Query: SELECT * FROM users WHERE email=?
  ↓
IF User Found:
  ↓
  Generate 6-digit code: random.randint(100000, 999999)
  ↓
  INSERT INTO password_reset_codes
  (user_id, code, expires_at, created_at)
  VALUES (?, ?, NOW() + 15 minutes, NOW())
  ↓
  Send email with code (Resend API)
  ↓
  Display: "Check your email"
  ↓
  User enters code
  ↓
  Query: SELECT * FROM password_reset_codes 
         WHERE user_id=? AND code=? AND expires_at > NOW()
  ↓
  IF Code Valid:
    ↓
    Display: "Enter new password"
    ↓
    User enters new password
    ↓
    Validate password strength:
      - Min 8 characters
      - At least 1 uppercase
      - At least 1 lowercase
      - At least 1 number
    ↓
    UPDATE users SET password_hash=? WHERE id=?
    ↓
    DELETE FROM password_reset_codes WHERE user_id=?
    ↓
    Display: "Password reset successful"
  ELSE:
    ↓
    Display: "Invalid or expired code"
ELSE:
  ↓
  Display: "Email not found"
```


### C. Role-Based Access Control
```
User accesses protected route
  ↓
Check authentication: current_user.is_authenticated?
  ↓
IF Not Authenticated:
  ↓
  Redirect to /login
ELSE:
  ↓
  Check role authorization:
    - /admin/* → Requires role='admin' OR role='loan_officer'
    - /loan/* → Requires role='loan_staff'
    - /ci/* → Requires role='ci_staff'
  ↓
  IF Authorized:
    ↓
    Check specific permissions (for loan_officer):
      - view_reports
      - manage_users
      - ci_tracking
    ↓
    IF Has Permission:
      ↓
      Allow access
    ELSE:
      ↓
      Display: "Unauthorized - Permission required"
  ELSE:
    ↓
    Display: "Unauthorized - Role required"
    ↓
    Redirect to appropriate dashboard
```

---

## 9. SYSTEM STATISTICS & REPORTS

### A. Dashboard Statistics
```
Admin Dashboard
  ↓
Query Statistics:
  ↓
  Total Applications:
    SELECT COUNT(*) FROM loan_applications
  ↓
  Pending Review:
    SELECT COUNT(*) FROM loan_applications 
    WHERE status='ci_completed'
  ↓
  In Process:
    SELECT COUNT(*) FROM loan_applications 
    WHERE status IN ('submitted', 'assigned_to_ci')
  ↓
  Approved:
    SELECT COUNT(*) FROM loan_applications 
    WHERE status='approved'
  ↓
  Disapproved:
    SELECT COUNT(*) FROM loan_applications 
    WHERE status='disapproved'
  ↓
  Total Loan Amount Approved:
    SELECT SUM(loan_amount) FROM loan_applications 
    WHERE status='approved'
  ↓
  Active CI Staff:
    SELECT COUNT(*) FROM users 
    WHERE role='ci_staff' AND is_online=1
  ↓
Display Statistics on Dashboard
```


### B. Generate Reports
```
Admin clicks "Generate Report"
  ↓
Select Report Type:
  - Applications by Status
  - Applications by Date Range
  - Applications by CI Staff
  - Approval Rate Analysis
  - Loan Amount Summary
  ↓
Select Date Range (optional)
  ↓
Query Database:
  ↓
  Applications by Status:
    SELECT status, COUNT(*) as count, SUM(loan_amount) as total_amount
    FROM loan_applications
    GROUP BY status
  ↓
  Applications by Date Range:
    SELECT * FROM loan_applications
    WHERE submitted_at BETWEEN ? AND ?
    ORDER BY submitted_at DESC
  ↓
  Applications by CI Staff:
    SELECT u.name, COUNT(*) as total_assigned, 
           SUM(CASE WHEN la.status='ci_completed' THEN 1 ELSE 0 END) as completed
    FROM loan_applications la
    JOIN users u ON la.assigned_ci_staff = u.id
    GROUP BY u.name
  ↓
  Approval Rate:
    SELECT 
      COUNT(*) as total,
      SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved,
      SUM(CASE WHEN status='disapproved' THEN 1 ELSE 0 END) as disapproved,
      (SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as approval_rate
    FROM loan_applications
    WHERE status IN ('approved', 'disapproved')
  ↓
Generate Report File:
  - Excel (XLSX): Use openpyxl library
  - PDF: Use reportlab library
  - CSV: Use csv library
  ↓
Download Report
  ↓
Back to Dashboard
```

---

## 10. ERROR HANDLING & LOGGING

### A. Database Error Handling
```
Try to execute database operation
  ↓
TRY:
  ↓
  conn = get_db()
  ↓
  Execute query
  ↓
  conn.commit()
  ↓
  conn.close()
  ↓
  Success
EXCEPT Exception as e:
  ↓
  conn.rollback()
  ↓
  conn.close()
  ↓
  Log error: print(f"Database error: {str(e)}")
  ↓
  Display user-friendly error message
  ↓
  Redirect to safe page
```


### B. File Upload Error Handling
```
User uploads file
  ↓
Validate file:
  ↓
  Check file exists: if not file or not file.filename
  ↓
  Check file extension: if not allowed_file(filename)
  ↓
  Check file size: if file.size > 16MB
  ↓
IF Validation Fails:
  ↓
  Display error message
  ↓
  Return to upload form
ELSE:
  ↓
  TRY:
    ↓
    Save file to server
    ↓
    Insert into database
    ↓
    Success
  EXCEPT Exception as e:
    ↓
    Delete uploaded file (if exists)
    ↓
    Log error
    ↓
    Display error message
```

### C. API Error Handling
```
Call External API (SMS/Email)
  ↓
TRY:
  ↓
  Send API request
  ↓
  Wait for response (timeout: 10 seconds)
  ↓
  IF Response Success:
    ↓
    Log success
    ↓
    Continue
  ELSE:
    ↓
    Log API error
    ↓
    Display warning (but don't block operation)
EXCEPT Timeout:
  ↓
  Log timeout error
  ↓
  Display warning
EXCEPT Exception as e:
  ↓
  Log exception
  ↓
  Display warning
```

---

## 11. DEPLOYMENT & ENVIRONMENT

### A. Local Development (SQLite)
```
Environment: Development
  ↓
Database: SQLite (app.db)
  ↓
.env Configuration:
  DATABASE_URL=sqlite:///app.db
  FLASK_ENV=development
  FLASK_DEBUG=True
  ↓
Run Application:
  python app.py
  ↓
Access: http://localhost:5000
```


### B. Production Deployment (Render + PostgreSQL)
```
Environment: Production
  ↓
Database: PostgreSQL (Render)
  ↓
.env Configuration:
  DATABASE_URL=postgresql://dccco_app:password@host/dbs_txpj
  FLASK_ENV=production
  FLASK_DEBUG=False
  ↓
Render Build Command:
  pip install -r requirements.txt
  ↓
Render Start Command:
  gunicorn app:app
  ↓
Database Migration:
  - Tables auto-created on first run
  - Default users created (admin, loan_officer, ci_staff, loan_staff)
  - Default loan types created (18 types)
  - Default system settings created
  ↓
Access: https://your-app.onrender.com
  ↓
Data Persistence: Forever (PostgreSQL)
```

---

## 12. DEFAULT USERS & CREDENTIALS

```
┌─────────────────────────────────────────────────────────────┐
│                    DEFAULT USER ACCOUNTS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Super Admin                                             │
│     Email: superadmin@dccco.test                            │
│     Password: admin@2024                                    │
│     Role: admin                                             │
│     Permissions: ALL                                        │
│                                                              │
│  2. Loan Officer                                            │
│     Email: admin@dccco.test                                 │
│     Password: admin123                                      │
│     Role: loan_officer                                      │
│     Permissions: Configurable                               │
│                                                              │
│  3. LPS Staff                                               │
│     Email: loan@dccco.test                                  │
│     Password: loan123                                       │
│     Role: loan_staff                                        │
│     Permissions: Submit applications, view own applications │
│                                                              │
│  4. CI/BI Staff                                             │
│     Email: ci@dccco.test                                    │
│     Password: ci123                                         │
│     Role: ci_staff                                          │
│     Permissions: Conduct investigations, complete checklists│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```



---

## 13. LOAN TYPES (18 TYPES)

```
┌─────────────────────────────────────────────────────────────┐
│                    DCCCO LOAN TYPES                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  AGRICULTURAL LOANS:                                        │
│  1. Agricultural with Chattel                               │
│  2. Agricultural with REM (Real Estate Mortgage)            │
│  3. Agricultural w/o Collateral                             │
│                                                              │
│  BUSINESS LOANS:                                            │
│  4. Business with Chattel                                   │
│  5. Business with REM                                       │
│  6. Business w/o Collateral                                 │
│                                                              │
│  MULTIPURPOSE LOANS:                                        │
│  7. Multipurpose with Chattel                               │
│  8. Multipurpose with REM                                   │
│  9. Multipurpose w/o Collateral                             │
│                                                              │
│  SALARY LOANS:                                              │
│  10. Salary ATM - Dim                                       │
│  11. Salary MOA - Dim                                       │
│                                                              │
│  CAR LOANS:                                                 │
│  12. Car Loan - Dim (surplus)                               │
│  13. Car Loan (Brand New) - Dim                             │
│                                                              │
│  SPECIAL LOANS:                                             │
│  14. Back-to-back Loan                                      │
│  15. Pension Loan                                           │
│  16. Hospitalization Loan                                   │
│  17. Petty Cash Loan                                        │
│  18. Incentive Loan                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. CI ROUTES (6 ROUTES)

```
┌─────────────────────────────────────────────────────────────┐
│                    CI STAFF ROUTES                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Route 1: Bayawan - Kalumboyan Area                         │
│  Barangays: Kalumboyan, Kalamtukan, Malabugas, Bugay, Nangka│
│                                                              │
│  Route 2: Bayawan - Basay Area                              │
│  Barangays: Basay, Actin, Bal-os, Bongalonan, Cabalayongan, │
│             Maglinao, Nagbo-alao, Olandao                    │
│                                                              │
│  Route 3: Bayawan - Sipalay Area                            │
│  Barangays: Sipalay, Cabadiangan, Camindangan, Canturay,    │
│             Cartagena, Mambaroto, Maricalum                  │
│                                                              │
│  Route 4: Bayawan - Santa Catalina Area                     │
│  Barangays: Santa Catalina, Alangilan, Amio, Buenavista,    │
│             Caigangan, Cawitan, Manalongon, Milagrosa,       │
│             Obat, Talalak                                    │
│                                                              │
│  Route 5: Bayawan Center                                    │
│  Barangays: Ali-is, Banaybanay, Banga, Boyco, Cansumalig,   │
│             Dawis, Manduao, Maninihon, Minaba, Narra,        │
│             Pagatban, Poblacion, San Isidro, San Jose,       │
│             San Miguel, San Roque, Suba, Tabuan, Tayawan,    │
│             Tinago, Ubos, Villareal, Villasol                │
│                                                              │
│  Route 6: Bayawan - Omod Area                               │
│  Barangays: Omod, Tamisu                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## SUMMARY

This flowchart document provides a complete visual representation of the DCCCO Loan Management System, including:

✅ All 4 user role workflows (Super Admin, Loan Officer, LPS Staff, CI/BI Staff)
✅ Complete database schema with all tables and relationships
✅ Detailed application lifecycle from submission to decision
✅ Real-time features (messaging, notifications, GPS tracking, dashboard updates)
✅ External service integrations (SMS, Email, File Storage)
✅ Security & authentication flows
✅ Error handling & logging
✅ Deployment configurations
✅ Default users, loan types, and CI routes

The system uses:
- Backend: Flask (Python)
- Database: PostgreSQL (production) / SQLite (development)
- Real-time: Socket.IO
- Frontend: HTML, CSS, JavaScript
- Deployment: Render
- SMS: Semaphore API
- Email: Resend API

All data persists forever in PostgreSQL, and the system supports 163 applications with complete data from LPS → CI/BI → Loan Officer workflow.

