# Testing Instructions for CI Checklist Wizard

## What Was Completed

I've successfully completed the 5-page CI Checklist Wizard that matches your exact paper forms:

1. **Page 1: Personal Data** - Applicant/Spouse info, Family Background, Residence, Court Checking, Employment
2. **Page 2: Credit Checking + Membership** - Business info, Credit history, DCCCO membership status
3. **Page 3: Computation** - Income, Loans, Expenses with DYNAMIC AUTO-CALCULATIONS
4. **Page 4: Credit Assessment Summary** - Capacity, Character, Collateral, Condition (4 C's)
5. **Page 5: Recommendation/Action** - Approval hierarchy, Signature pad, GPS location, Submit

## How to Test

### Step 1: Login as CI Staff
1. Go to your application: https://ci-staff-app-zag3.onrender.com/
2. Login with CI staff credentials:
   - Email: `ci@dccco.test`
   - Password: `ci@2024`

### Step 2: Open an Application
1. You'll see your CI Dashboard
2. Click on any application assigned to you
3. You'll see the application details page

### Step 3: Open the Full Checklist
1. At the top of the page, click the blue button: **"Open Full Checklist (5 Pages)"**
2. This will open the new wizard

### Step 4: Fill Out the Wizard
1. **Page 1** - Fill in personal data, family info, residence, employment
   - Click "Next Page" when done
2. **Page 2** - Fill in business info, credit checking, membership status
   - Click "Next" when done
3. **Page 3** - Fill in income and expenses
   - **WATCH THE MAGIC**: As you type numbers, all calculations update automatically!
   - Try entering:
     - Gross Pay: 25000
     - Allowances: 5000
     - Watch "Net Pay" calculate automatically
     - Watch "Total Gross Income" update
     - Enter some expenses and watch "Debt & Expense Ratio" calculate
   - Click "Add Loan" to add more loan rows
   - Click "Next" when done
4. **Page 4** - Fill in credit assessment (Capacity, Character, Collateral, Condition)
   - Check YES/NO boxes
   - Fill in other info
   - Click "Next" when done
5. **Page 5** - Final page
   - Check approval/disapprove boxes for each position
   - **Draw your signature** in the signature pad
   - Click "Clear Signature" if you make a mistake
   - Upload photos (optional)
   - Click **"Submit Complete Checklist"**
   - GPS location will be captured automatically
   - Form will submit to Loan Officer

### Step 5: View as Loan Officer
1. Logout from CI staff account
2. Login as Loan Officer:
   - Email: `loan_officer@dccco.test`
   - Password: `loan@2024`
3. Go to Loan Officer Dashboard
4. Find the application you just submitted
5. Click "View Checklist" to see all the data
6. Click "Print" to print the checklist

## What to Look For

### ✓ Navigation
- [ ] Can navigate between pages using Previous/Next buttons
- [ ] Can jump to any page using the circular buttons (1-5) on the right
- [ ] Current page is highlighted in blue
- [ ] Completed pages show in green

### ✓ Dynamic Calculations (Page 3)
- [ ] Net Pay calculates when you enter Gross Pay, Allowances, PERA, Long Pay, Deductions
- [ ] Total Gross Income updates when you add Other Income
- [ ] Can add/remove loan rows
- [ ] Total Loan Amortizations updates when you enter loan amounts
- [ ] Total Before New Loan calculates
- [ ] New Loan calculates (Applied - Deductible)
- [ ] Total Obligations calculates from all expenses
- [ ] Net Disposable Income calculates (Income - Loans - Obligations)
- [ ] Debt & Expense Ratio calculates as percentage
- [ ] Loan Amortization Limit calculates (80% of income)

### ✓ Data Persistence
- [ ] Fill out some fields, wait 30 seconds (auto-save)
- [ ] Refresh the page
- [ ] Data should still be there (saved to localStorage)

### ✓ Signature Pad
- [ ] Can draw signature with mouse/touch
- [ ] Clear button works
- [ ] Cannot submit without signature

### ✓ GPS Location
- [ ] When you click Submit, browser asks for location permission
- [ ] Location is captured and displayed
- [ ] Form submits successfully

### ✓ Loan Officer View
- [ ] Can see all filled data
- [ ] Can print the checklist
- [ ] All pages show correctly

## Expected Behavior

1. **First time opening**: All fields are empty
2. **After filling some fields**: Data auto-saves every 30 seconds
3. **After refreshing**: Data persists from localStorage
4. **After submitting**: Data is saved to database, localStorage is cleared
5. **Loan Officer view**: Shows all submitted data in a printable format

## Troubleshooting

### If calculations don't work:
- Check browser console for JavaScript errors (F12)
- Make sure you're entering numbers, not text
- Try refreshing the page

### If signature pad doesn't work:
- Make sure you're clicking inside the canvas area
- Try using a different browser
- Check if JavaScript is enabled

### If GPS doesn't work:
- Make sure you allow location permission when browser asks
- Check if location services are enabled on your device
- Try using HTTPS (required for geolocation)

### If data doesn't save:
- Check if localStorage is enabled in your browser
- Check browser console for errors
- Try clearing browser cache and cookies

## Files Modified

1. `templates/ci_checklist_wizard.html` - Complete 5-page wizard (1013 lines)
2. `templates/ci_application.html` - Updated button text to "5 Pages"
3. `static/ci-checklist-wizard.js` - Updated totalPages to 5
4. `CI_CHECKLIST_WIZARD_COMPLETE.md` - Complete documentation

## Next Steps After Testing

1. If everything works correctly, commit and push to GitHub
2. Render will automatically deploy the changes
3. Test on production site
4. If any issues, let me know and I'll fix them immediately

## Questions?

If you encounter any issues or have questions, please let me know:
- What page were you on?
- What were you trying to do?
- What happened vs what you expected?
- Any error messages?

I'm here to help make sure everything works perfectly!
