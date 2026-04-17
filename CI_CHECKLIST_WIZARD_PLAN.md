# CI Checklist Wizard Implementation Plan

## Overview
Creating a multi-page wizard that exactly matches the DCCCO paper forms with added checkboxes and dynamic calculations.

## 8-Page Structure

### Page 1: Personal Data (APPLICANT & SPOUSE)
**From your form image 5**
- Last Name, First Name, Middle Name (Applicant & Spouse columns)
- Birthday, Age
- Family Background table (Name of Parents and Children, Age, Relationship, Member/Non-Member)
- Residence Checking section
  - Present Address (House No, Street, Barangay, City/Municipality, Province)
  - Permanent Address
  - Residence Status checkboxes: Owned, Rented, Living with Parents, Mortgaged, Others
  - Type of House checkboxes: Concrete, Semi-Concrete, Wood, Shanty, Others
  - Row House, Duplex, Single-Detached, Split Type, Two-Storey, Condo Unit
  - Length of Stay (Years/Months)
  - Remarks field

### Page 2: Court & Employment Checking
**From your form image 5 (bottom section)**
- Court and Other Government Agency Checking
  - YES/NO checkboxes for:
    - Has record of complaints regarding money or debt
    - Has pending case for money judgment or sum of money or replevin, foreclosure, garnishment, insolvency
    - Has criminal record (Police/NBI clearance)
- Employment/Business Checking (APPLICANT & SPOUSE columns)
  - Employment Details
  - Employer
  - Office Address
  - Date of Organization (Employer's Business)
  - Contact Number of Employer
  - Status of Employment: Permanent, Casual, Contractual, Probationary, Others
  - Length of Service (Years/Months)
  - Type of Organization: Government Institution, Military and Uniformed Personnel, Depot, Others
  - Private Institution: Small, Medium, Large
  - Business Processing Outsourcing (BPO)

### Page 3: Credit Checking
**From your form image 1**
- Business Name
- Address
- Nature: Sole Proprietorship, Partnership, Corporation, Service, Manufacturing, Others
- Years in Business
- Credit Checking table with columns:
  - Electric Company
  - Water/Utility Company
  - Other Cooperatives
  - N/A
  - Banks
  - Other Financial Institutions
  - N/A
  - Sari-sari Store
  - N/A
  - Loans with Informal Lenders
  - N/A
- Each row has: Updated/NRCS, Delayed/Non-NRCS, Remarks columns

### Page 4: Membership Status with DCCCO
**From your form image 1 (bottom section)**
- Membership Classification checkboxes:
  - New Member, NRCS, Non-NRCS
- Loan Accounts with DCCCO (last attached SDA):
  - No Loan, 1-2 Filers, More than 2 Filers, Past Due, Restructured
- Outstanding loan accounts within 12 months:
  - No Loan, 1-2 Filers, More than 2 Filers, Past Due, Restructured
- Other Loan Accounts:
  - Niskal, Bronze, Silver, Gold, Platinum
- Date Reported
- Date Investigated
- Prepared by: Credit Investigator
- Reviewed by: Head, Credit Investigator
- Noted by: Credit Officer

### Page 5: Computation of Debt and Expense-to-Income Ratio
**From your form image 2 - WITH DYNAMIC CALCULATIONS**
- Header: DCCCO Multipurpose Cooperative, Branch, Date
- Name of Member, Applied Loan
- Membership Classification, Applied Amount
- Occupation

#### INCOME Section (Auto-calculates):
- Gross Pay: ₱_____
- Add: Allowances/Benefits (Received monthly): 0.00
- PERA/ACA: 0.00
- Long Pay: ₱_____
- Less: Statutory Deductions (all deductions reflected on the pay slip): ₱_____
- **Net Pay** = Auto-calculated

#### Other Income (with proof):
- Income from Business/Salary Permit/ITR, Audited FS: ₱_____ (0.00)
- Remittance from Abroad/ATM Card: 0.00
- Allotment (Base Statement, Certificate of Allotment): 0.00
- Others (with documents to support): 0.00, 0.00, ₱_____
- **Total Gross Income** = Auto-sum

#### LOAN AMORTIZATIONS & OTHER OBLIGATIONS/EXPENSES:
- LOAN AMORTIZATIONS (Dynamic rows - can add/remove):
  - From Other Institutions: N/A, ₱_____, ₱_____, ₱_____
  - Multiple rows possible
  - Sub-total: ₱_____

- DCCCO Loans (existing): (Dynamic rows)
  - Multiple loan entries
  - Sub-total: ₱_____
  - **Total Loans/Amortizations before New Loan**: ₱_____

- Add: Loan applied for: 0.00
- Less: Loan's deductible from proceeds: ₱_____, ₱_____, ₱_____, ₱_____
- **New Loan**: 0.00, 0.00

#### OTHER OBLIGATIONS/EXPENSES:
- Household Expenses (₱3,500.00 per family member): ₱_____
- Tuition & other school expenses: _____
- Medical/Hospitalization: _____
- Water & Fuel consumption: _____
- Internet/Cellphone load: _____
- **TOTAL LOAN AMORTIZATIONS & OTHER OBLIGATIONS/EXPENSES**: 0.00, ₱_____
- **Net Disposable Income**: ₱_____

#### Final Calculations:
- **Debt & Expense to Income Ratio** (80% maximum): #DIV/0!, ₱_____
- **Total Loan Amortization Limit** (80% of Total Gross Income): #DIV/0!

- Prepared by: NICKANTES V. EMBANG, CIRI / FFS / FLMS
- Noted by: RAMON E. ESPARCIA, III, Credit Officer
- BOA Res. No. 182-3, 2022 (March 21, 2022)

### Page 6: Credit Assessment Summary
**From your form image 4**
- DCCCO Multipurpose Cooperative
- Branch, Date
- CREDIT ASSESSMENT SUMMARY

#### Member Information:
- Name of Member, Type of Loan
- Age, Loan Amount
- Membership Classification, Purpose
- Years of Membership, Term
- Account with DCCCO: Good Attendance (₱___), Amortization

#### CREDIT AND BACKGROUND INVESTIGATION:
- CAPACITY section with YES/NO checkboxes:
  - DEIR (Debt & Expense to Income Ratio) is within limit (see Attachment 2 - DEIR)
  - Net Take Home Pay (if Salary Loan) is within limit (see Attachment 3 - NTHP)
  - Other Info: Borrower, Employer, Tenure
  - Salary: _____
  - Company category/Maximum Loanable Amount: N/A
  - Business: _____, Years: _____, Monthly Income: _____
  - Spouse: Employer/Business, Salary/Business Income

#### CHARACTER section with YES/NO checkboxes:
- DCCCO Credit History in the last twelve (12) months:
  - Loans are current and never fined
  - Loans were fined/past due: 1___, 2 or more fines
  - PSM Loan
- Without negative feedback from other institutions (coop/lending/utility/telco)
- Without negative feedback from neighbors/co-workers/barangay/court

#### COLLATERAL section:
- REM: OCT No: N/A, Location: N/A, Loan Value: N/A, Area (sq. m.): N/A
- Chattel: Type: N/A, With Right of Way: Yes___ No___, Loan Value: N/A
- Others: N/A, N/A

#### CONDITION section with YES/NO checkboxes:
- Health: Able to perform daily routine tasks
- Not taking regular/maintenance medication
- Business (if any):
  - Business has updated permits (Business, BIR, DTI,etc)
  - Nature of business is legal (Please state below the details)

#### OTHER INFORMATION:
- Multiple blank lines for notes

- Prepared by: _____, Reviewed by: _____
- CIRI / FLMS, Head, CIRI
- Page 1 of 2

### Page 7: Recommendation/Action
**From your form image 3**
- RECOMMENDATION/ACTION
- SIGNATURE/DATE column

#### Approval Hierarchy:
- Credit Officer: □ Approve □ Disapprove □ Defer, Remarks: _____
- CM: □ Approve □ Disapprove □ Defer, Remarks: _____
- OM: □ Approve □ Disapprove □ Defer, Remarks: _____
- Management Credit Committee: □ Approve □ Disapprove □ Defer, Remarks: _____
- FTM: □ Approve □ Disapprove □ Defer, Remarks: _____
- CEO: □ Approve □ Disapprove □ Defer, Remarks: _____
- Board of Directors: □ Approve □ Disapprove, Remarks: _____

#### Legend:
- DEIR - Debt and Expense to Income Ratio
- NTHP - Net Take Home Pay Computation

- ISO Reg. No. 187, s. 2022 (March 21, 2022)
- page 2 of 2

### Page 8: Final Review & Submit
- Summary of all entered data
- Signature pad for CI Staff
- Upload photos section
- GPS location capture
- Submit button

## Key Features

### Dynamic Calculations (Page 5):
- All income fields auto-sum to Total Gross Income
- Net Pay = Gross + Allowances + PERA + Long - Deductions
- Loan amortizations auto-sum
- Other obligations auto-sum
- Net Disposable Income = Total Income - Total Loans - Total Obligations
- Debt & Expense Ratio = (Loans + Obligations) / Total Income * 100
- Loan Amortization Limit = Total Income * 0.80
- Real-time updates as user types

### Navigation:
- Progress bar showing 8 steps
- Previous/Next buttons on each page
- Can jump to any page by clicking progress bar
- Auto-save every 30 seconds to localStorage
- Page validation before moving forward

### User Experience:
- Exact same layout as paper forms
- Checkboxes for all yes/no items
- Radio buttons for single-choice items
- Input fields match paper form structure
- Mobile-responsive design
- Print-friendly (all pages print together)

### Data Storage:
- All data stored in JSON format
- Saved to database on final submit
- Can resume incomplete checklist
- Can edit after submission

## Files Created:
1. `static/ci-checklist-wizard.css` - Styling ✓
2. `static/ci-checklist-wizard.js` - Logic ✓
3. `templates/ci_checklist_wizard.html` - Main template (TO CREATE)
4. Backend route in `app.py` (TO UPDATE)

## Next Steps:
1. Create the full HTML template with all 8 pages
2. Add route in app.py to handle the wizard
3. Test all calculations
4. Test navigation
5. Test data persistence
