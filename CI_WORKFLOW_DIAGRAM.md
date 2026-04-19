# CI Workflow - Complete Flow Diagram

## New Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        LPS SUBMITS APPLICATION                   │
│  - Fills basic info (name, address, loan amount, etc.)          │
│  - UPLOADS MULTIPLE IMAGES of loan application forms            │
│  - System runs OCR on images to extract data                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOAN OFFICER ASSIGNS TO CI                    │
│  - Reviews application in "In Process" tab                       │
│  - Assigns to available CI staff                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CI DASHBOARD                                │
│  - CI sees assigned application                                 │
│  - Clicks on application to start review                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: REVIEW PAGE (NEW!)                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Application Information:                                  │  │
│  │  - Member name, contact, address                          │  │
│  │  - Loan amount, loan type                                 │  │
│  │  - Submitted by (LPS name)                                │  │
│  │  - Submitted date                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Uploaded Documents & Photos:                             │  │
│  │  📷 Image 1 (DCCCO Form Page 1)                          │  │
│  │  📷 Image 2 (DCCCO Form Page 2)                          │  │
│  │  📷 Image 3 (ID Photo)                                    │  │
│  │  📄 PDF Document                                          │  │
│  │  [Click to view full size / Download]                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  [Fill Interview Checklist] Button                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│         STEP 2: CHECKBOX SUMMARY PAGE (NEW!)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Progress: [████████░░] 80% (96 of 120 items)            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  📋 Residence Status:                                           │
│  ☑ Owned  ☐ Rented  ☑ Living with Parents  ☐ Mortgaged        │
│                                                                  │
│  🏠 Type of House:                                              │
│  ☑ Concrete  ☐ Semi-Concrete  ☐ Wood  ☐ Shanty                │
│                                                                  │
│  🛡️ Court Records:                                              │
│  ☐ YES ☑ NO - Has record of complaints                         │
│  ☐ YES ☑ NO - Has pending case                                 │
│  ☐ YES ☑ NO - Has criminal record                              │
│                                                                  │
│  💼 Employment Status - Applicant:                              │
│  ☑ Permanent  ☐ Casual  ☐ Contractual                          │
│                                                                  │
│  💼 Employment Status - Spouse:                                 │
│  ☐ Permanent  ☑ Casual  ☐ Contractual                          │
│                                                                  │
│  🏪 Business Nature:                                            │
│  ☑ Sole Proprietorship  ☐ Partnership  ☐ Corporation           │
│                                                                  │
│  💳 Credit Checking:                                            │
│  Electric: ☑ Updated  ☐ Delayed                                │
│  Water: ☑ Updated  ☐ Delayed                                   │
│  Banks: ☐ Updated  ☐ Delayed  ☑ N/A                            │
│                                                                  │
│  👤 Membership Status:                                          │
│  ☐ New Member  ☑ NRCS  ☐ Non-NRCS                              │
│  ☑ No Loan  ☐ 1-2 Filers  ☐ More than 2                        │
│                                                                  │
│  📊 Capacity Assessment:                                        │
│  ☑ YES ☐ NO - DEIR within limit                                │
│  ☑ YES ☐ NO - NTHP within limit                                │
│                                                                  │
│  ✅ Character Assessment:                                       │
│  ☑ YES ☐ NO - Loans current, never fined                       │
│  ☑ YES ☐ NO - No negative feedback                             │
│                                                                  │
│  📝 Recommendations:                                            │
│  Credit Officer: ☑ Approve  ☐ Disapprove  ☐ Defer              │
│  Credit Manager: ☑ Approve  ☐ Disapprove  ☐ Defer              │
│  ... (all positions)                                            │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  [Proceed to 5-Page Form] Button                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (Saves checkbox data to session storage)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 3: 5-PAGE WIZARD (AUTO-FILLED!)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🎉 Checkbox Summary Loaded!                              │  │
│  │  ✨ AI Auto-Fill Complete!                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PAGE 1: Personal Data                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Applicant:                                                │  │
│  │  Last Name: [DELA CRUZ] ← OCR auto-filled                 │  │
│  │  First Name: [JONA] ← OCR auto-filled                     │  │
│  │  Middle Name: [RULANDA] ← OCR auto-filled                 │  │
│  │  Birthday: [16/05/2000] ← OCR auto-filled                 │  │
│  │  Age: [24] ← OCR auto-filled                              │  │
│  │                                                            │  │
│  │  Residence Status:                                         │  │
│  │  ☑ Owned ← From checkbox summary                          │  │
│  │  ☑ Living with Parents ← From checkbox summary            │  │
│  │                                                            │  │
│  │  Type of House:                                            │  │
│  │  ☑ Concrete ← From checkbox summary                       │  │
│  │                                                            │  │
│  │  Court Records:                                            │  │
│  │  ☑ NO - Has record of complaints ← From checkbox summary  │  │
│  │  ☑ NO - Has pending case ← From checkbox summary          │  │
│  │  ☑ NO - Has criminal record ← From checkbox summary       │  │
│  │                                                            │  │
│  │  Employment Status:                                        │  │
│  │  ☑ Permanent ← From checkbox summary                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PAGE 2: Credit Checking + Membership                           │
│  (All checkboxes already filled from summary)                   │
│                                                                  │
│  PAGE 3: Computation                                            │
│  (Text fields auto-filled from OCR, calculations automatic)     │
│                                                                  │
│  PAGE 4: Credit Assessment Summary                              │
│  (All checkboxes already filled from summary)                   │
│                                                                  │
│  PAGE 5: Recommendation/Action                                  │
│  (All checkboxes already filled from summary)                   │
│  - Add signature                                                │
│  - Upload photos                                                │
│  - GPS location captured                                        │
│  - Submit complete checklist                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKLIST SUBMITTED                           │
│  - Application status updated to "ci_completed"                 │
│  - Loan officer can now review and make decision                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Benefits of New Workflow

### 1. Review Page
- CI can see all documents and photos BEFORE starting checklist
- Can zoom in on images to verify details
- Can download documents for offline review
- Clear overview of application details

### 2. Checkbox Summary Page
- **100+ checkboxes** organized in one page
- **Progress tracking** shows completion percentage
- **Fast data entry** - no need to navigate between pages
- **Visual organization** - grouped by category with icons
- **Real-time updates** - progress bar updates as you check

### 3. 5-Page Wizard (Auto-Filled)
- **Checkboxes pre-filled** from summary page
- **Text fields pre-filled** from OCR (AI extracted from images)
- **Calculations automatic** (income, expenses, ratios)
- **Signature pad** for digital signature
- **GPS tracking** for location verification
- **Photo upload** for CI visit documentation

## Data Flow

```
LPS Images → OCR Extraction → Session Storage
                                    ↓
CI Checkbox Summary → Session Storage
                                    ↓
5-Page Wizard ← Loads both checkbox + OCR data
                                    ↓
                            Complete Form Submission
```

## Time Savings

### Old Workflow (Without Summary Page):
- Navigate through 5 pages
- Fill checkboxes scattered across pages
- Easy to miss checkboxes
- Time: ~20-30 minutes

### New Workflow (With Summary Page):
- Review documents: 2-3 minutes
- Fill all checkboxes in one page: 5-7 minutes
- Review and complete 5-page form: 5-8 minutes
- **Total Time: ~12-18 minutes** (40% faster!)

## Status: ✅ READY FOR PRODUCTION
