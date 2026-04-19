// CI Checklist Wizard JavaScript

let currentPage = 1;
const totalPages = 5;
let checklistData = {};

// Initialize wizard
document.addEventListener('DOMContentLoaded', function() {
    loadSavedData();
    loadCheckboxData(); // Load checkbox data from summary page
    loadOCRData(); // Load OCR extracted data if available
    loadVerificationData(); // Load CI verification checkbox data
    updateProgressBar();
    setupAutoSave();
    setupComputationListeners();
});

// Load checkbox data from summary page
function loadCheckboxData() {
    const checkboxData = sessionStorage.getItem('ci_checkbox_data');
    if (checkboxData) {
        try {
            const data = JSON.parse(checkboxData);
            
            // Apply checkbox data to form
            Object.keys(data).forEach(key => {
                const checkbox = document.querySelector(`[name="${key}"]`);
                if (checkbox && checkbox.type === 'checkbox') {
                    checkbox.checked = data[key];
                    // Highlight auto-filled checkboxes
                    if (data[key]) {
                        checkbox.parentElement.style.backgroundColor = '#f0fff4';
                        setTimeout(() => {
                            checkbox.parentElement.style.backgroundColor = '';
                        }, 3000);
                    }
                }
            });
            
            // Show notification
            showCheckboxNotification();
            
            // Clear session storage after loading
            sessionStorage.removeItem('ci_checkbox_data');
        } catch (e) {
            console.error('Error loading checkbox data:', e);
        }
    }
}

// Show checkbox notification
function showCheckboxNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        <h6><i class="bi bi-check2-square"></i> Checkbox Summary Loaded!</h6>
        <p class="mb-0 small">All checkboxes from the summary page have been applied. Review and complete the remaining fields.</p>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Load CI verification data from session storage
function loadVerificationData() {
    const verificationData = sessionStorage.getItem('ci_verification_data');
    if (verificationData) {
        try {
            const data = JSON.parse(verificationData);
            
            // Show notification that verification was completed
            showVerificationNotification(data);
            
            // You can use this data to pre-fill or validate fields
            console.log('Verification data loaded:', data);
            
            // Clear session storage after loading
            sessionStorage.removeItem('ci_verification_data');
        } catch (e) {
            console.error('Error loading verification data:', e);
        }
    }
}

// Show verification notification
function showVerificationNotification(data) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        <h6><i class="bi bi-check-circle"></i> Document Verification Complete!</h6>
        <p class="mb-0 small">All required documents have been verified. You can now proceed with the interview.</p>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}


// Load OCR extracted data from session storage
function loadOCRData() {
    const ocrData = sessionStorage.getItem('ocr_extracted_data');
    if (ocrData) {
        try {
            const data = JSON.parse(ocrData);
            autoFillFromOCR(data);
            
            // Show notification
            showOCRNotification();
            
            // Clear session storage after loading
            sessionStorage.removeItem('ocr_extracted_data');
        } catch (e) {
            console.error('Error loading OCR data:', e);
        }
    }
}

// Auto-fill form from OCR data
function autoFillFromOCR(data) {
    console.log('Auto-filling from OCR data:', data);
    
    // Page 1: Personal Data - Applicant
    if (data.applicant) {
        setFieldValue('applicant_last_name', data.applicant.last_name);
        setFieldValue('applicant_first_name', data.applicant.first_name);
        setFieldValue('applicant_middle_name', data.applicant.middle_name);
        setFieldValue('applicant_birthday', data.applicant.birthday);
        setFieldValue('applicant_age', data.applicant.age);
    }
    
    // Page 1: Personal Data - Spouse
    if (data.spouse) {
        setFieldValue('spouse_last_name', data.spouse.last_name);
        setFieldValue('spouse_first_name', data.spouse.first_name);
        setFieldValue('spouse_middle_name', data.spouse.middle_name);
        setFieldValue('spouse_birthday', data.spouse.birthday);
        setFieldValue('spouse_age', data.spouse.age);
    }
    
    // Page 1: Family Background
    if (data.family_background && data.family_background.length > 0) {
        data.family_background.forEach((member, index) => {
            if (index < 5) { // Limit to 5 family members
                setFieldValue(`family_name_${index + 1}`, member.name);
                setFieldValue(`family_age_${index + 1}`, member.age);
                setFieldValue(`family_relationship_${index + 1}`, member.relationship);
                setFieldValue(`family_member_status_${index + 1}`, member.member_status);
            }
        });
    }
    
    // Page 2: Address
    if (data.address) {
        if (data.address.full_address) {
            setFieldValue('address', data.address.full_address);
        }
        if (data.address.purok) {
            setFieldValue('purok', data.address.purok);
        }
        if (data.address.barangay) {
            setFieldValue('barangay', data.address.barangay);
        }
        if (data.address.municipality) {
            setFieldValue('municipality', data.address.municipality);
        }
        if (data.address.province) {
            setFieldValue('province', data.address.province);
        }
    }
    
    // Page 3: Income
    if (data.income && data.income.sources) {
        data.income.sources.forEach((source, index) => {
            if (index < 5) {
                setFieldValue(`income_source_${index + 1}`, source.description);
                setFieldValue(`income_amount_${index + 1}`, source.amount);
            }
        });
        if (data.income.total) {
            setFieldValue('total_income', data.income.total);
        }
    }
    
    // Page 3: Expenses
    if (data.expenses && data.expenses.items) {
        data.expenses.items.forEach((expense, index) => {
            if (index < 5) {
                setFieldValue(`expense_item_${index + 1}`, expense.description);
                setFieldValue(`expense_amount_${index + 1}`, expense.amount);
            }
        });
        if (data.expenses.total) {
            setFieldValue('total_expenses', data.expenses.total);
        }
    }
    
    // Page 4: Assets
    if (data.assets && data.assets.length > 0) {
        data.assets.forEach((asset, index) => {
            if (index < 5) {
                setFieldValue(`asset_${index + 1}`, asset);
            }
        });
    }
    
    // Page 4: Liabilities
    if (data.liabilities && data.liabilities.length > 0) {
        data.liabilities.forEach((liability, index) => {
            if (index < 5) {
                setFieldValue(`liability_${index + 1}`, liability);
            }
        });
    }
    
    // Page 4: Co-maker
    if (data.co_maker) {
        setFieldValue('co_maker_name', data.co_maker.name);
        setFieldValue('co_maker_address', data.co_maker.address);
        setFieldValue('co_maker_contact', data.co_maker.contact);
    }
    
    // Page 4: References
    if (data.references && data.references.length > 0) {
        data.references.forEach((reference, index) => {
            if (index < 3) {
                setFieldValue(`reference_${index + 1}`, reference);
            }
        });
    }
    
    // Trigger computations
    setTimeout(() => {
        computeAllTotals();
    }, 500);
}

// Helper function to set field value
function setFieldValue(fieldName, value) {
    if (!value) return;
    
    const field = document.querySelector(`[name="${fieldName}"]`);
    if (field) {
        field.value = value;
        field.style.backgroundColor = '#f0fff4'; // Light green highlight
        
        // Remove highlight after 3 seconds
        setTimeout(() => {
            field.style.backgroundColor = '';
        }, 3000);
    }
}

// Show OCR notification
function showOCRNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        <h6><i class="bi bi-magic"></i> AI Auto-Fill Complete!</h6>
        <p class="mb-0">Form fields have been automatically filled from uploaded images. Please review and correct any errors.</p>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Navigate to specific page
function goToPage(pageNumber) {
    if (pageNumber < 1 || pageNumber > totalPages) return;
    
    // Save current page data
    saveCurrentPageData();
    
    // Hide all pages
    document.querySelectorAll('.wizard-page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show target page
    const targetPage = document.querySelector(`.wizard-page[data-page="${pageNumber}"]`);
    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = pageNumber;
        updateProgressBar();
        window.scrollTo(0, 0);
    }
}

// Update progress bar
function updateProgressBar() {
    document.querySelectorAll('.page-btn').forEach((btn, index) => {
        const pageNumber = index + 1;
        btn.classList.remove('active', 'completed');
        
        if (pageNumber < currentPage) {
            btn.classList.add('completed');
        } else if (pageNumber === currentPage) {
            btn.classList.add('active');
        }
    });
}

// Save current page data
function saveCurrentPageData() {
    const currentPageElement = document.querySelector(`.wizard-page[data-page="${currentPage}"]`);
    if (!currentPageElement) return;
    
    // Get all form inputs in current page
    const inputs = currentPageElement.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            checklistData[input.name] = input.checked;
        } else if (input.type === 'radio') {
            if (input.checked) {
                checklistData[input.name] = input.value;
            }
        } else {
            checklistData[input.name] = input.value;
        }
    });
    
    // Save to localStorage
    localStorage.setItem('ci_checklist_draft', JSON.stringify(checklistData));
}

// Load saved data
function loadSavedData() {
    const saved = localStorage.getItem('ci_checklist_draft');
    if (saved) {
        try {
            checklistData = JSON.parse(saved);
            populateFormData();
        } catch (e) {
            console.error('Error loading saved data:', e);
        }
    }
}

// Populate form with saved data
function populateFormData() {
    Object.keys(checklistData).forEach(key => {
        const input = document.querySelector(`[name="${key}"]`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = checklistData[key];
            } else if (input.type === 'radio') {
                if (input.value === checklistData[key]) {
                    input.checked = true;
                }
            } else {
                input.value = checklistData[key];
            }
        }
    });
    
    // Trigger computation updates
    updateAllComputations();
}

// Auto-save every 30 seconds
function setupAutoSave() {
    setInterval(() => {
        saveCurrentPageData();
    }, 30000);
}

// Previous page
function previousPage() {
    if (currentPage > 1) {
        goToPage(currentPage - 1);
    }
}

// Next page
function nextPage() {
    if (currentPage < totalPages) {
        goToPage(currentPage + 1);
    }
}

// Submit form
function submitChecklist() {
    saveCurrentPageData();
    document.getElementById('checklist_data').value = JSON.stringify(checklistData);
    document.getElementById('ciChecklistForm').submit();
}

// Computation functions for Page 6
function setupComputationListeners() {
    // Income section
    const incomeFields = ['gross_pay', 'allowances', 'pera_aca', 'long_pay', 'statutory_deductions',
                         'income_business', 'remittance', 'allotment', 'other_income'];
    incomeFields.forEach(field => {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            input.addEventListener('input', updateAllComputations);
        }
    });
}

function updateAllComputations() {
    updateNetPay();
    updateTotalGrossIncome();
    updateLoanAmortizations();
    updateDCCCOLoans();
    updateTotalBeforeNew();
    updateNewLoan();
    updateOtherObligations();
    updateFinalCalculations();
}

function getNumericValue(name) {
    const input = document.querySelector(`[name="${name}"]`);
    return input ? parseFloat(input.value) || 0 : 0;
}

function setComputedValue(name, value) {
    const input = document.querySelector(`[name="${name}"]`);
    if (input) {
        input.value = value.toFixed(2);
    }
}

function updateNetPay() {
    const grossPay = getNumericValue('gross_pay');
    const allowances = getNumericValue('allowances');
    const pera = getNumericValue('pera_aca');
    const longPay = getNumericValue('long_pay');
    const deductions = getNumericValue('statutory_deductions');
    
    const netPay = grossPay + allowances + pera + longPay - deductions;
    setComputedValue('net_pay', netPay);
}

function updateTotalGrossIncome() {
    const netPay = getNumericValue('net_pay');
    const incomeBusiness = getNumericValue('income_business');
    const remittance = getNumericValue('remittance');
    const allotment = getNumericValue('allotment');
    const otherIncome = getNumericValue('other_income');
    
    const totalGrossIncome = netPay + incomeBusiness + remittance + allotment + otherIncome;
    setComputedValue('total_gross_income', totalGrossIncome);
}

function updateLoanAmortizations() {
    let total = 0;
    document.querySelectorAll('.loan-row').forEach(row => {
        const monthly = parseFloat(row.querySelector('[name$="_monthly"]')?.value) || 0;
        total += monthly;
    });
    setComputedValue('total_loan_amortizations', total);
    updateTotalBeforeNew();
}

function updateDCCCOLoans() {
    const loan1 = getNumericValue('dccco_loan_1');
    const loan2 = getNumericValue('dccco_loan_2');
    return loan1 + loan2;
}

function updateTotalBeforeNew() {
    const otherLoans = getNumericValue('total_loan_amortizations');
    const dcccoLoans = updateDCCCOLoans();
    const total = otherLoans + dcccoLoans;
    setComputedValue('total_before_new', total);
}

function updateNewLoan() {
    const applied = getNumericValue('new_loan_amount');
    const deductible = getNumericValue('loan_deductible');
    const newLoan = applied - deductible;
    setComputedValue('new_loan_final', newLoan);
}

function updateOtherObligations() {
    const household = getNumericValue('household_expenses');
    const tuition = getNumericValue('tuition');
    const medical = getNumericValue('medical');
    const water = getNumericValue('water_fuel');
    const internet = getNumericValue('internet');
    
    const total = household + tuition + medical + water + internet;
    setComputedValue('total_other_obligations', total);
}

function updateFinalCalculations() {
    const totalIncome = getNumericValue('total_gross_income');
    const totalBeforeNew = getNumericValue('total_before_new');
    const newLoan = getNumericValue('new_loan_final');
    const totalObligations = getNumericValue('total_other_obligations');
    
    const totalExpenses = totalBeforeNew + newLoan + totalObligations;
    const netDisposable = totalIncome - totalExpenses;
    setComputedValue('net_disposable_income', netDisposable);
    
    if (totalIncome > 0) {
        const ratio = (totalExpenses / totalIncome) * 100;
        setComputedValue('debt_expense_ratio', ratio);
        
        const loanLimit = totalIncome * 0.80;
        setComputedValue('loan_amortization_limit', loanLimit);
    } else {
        setComputedValue('debt_expense_ratio', 0);
        setComputedValue('loan_amortization_limit', 0);
    }
}

// Add dynamic loan row
function addLoanRow() {
    const container = document.getElementById('loan_rows_container');
    const rowCount = container.querySelectorAll('.loan-row').length + 1;
    
    const row = document.createElement('tr');
    row.className = 'loan-row';
    row.innerHTML = `
        <td><input type="text" name="loan_${rowCount}_institution" class="form-control form-control-sm"></td>
        <td><input type="number" name="loan_${rowCount}_principal" class="form-control form-control-sm" step="0.01"></td>
        <td><input type="number" name="loan_${rowCount}_balance" class="form-control form-control-sm" step="0.01"></td>
        <td><input type="number" name="loan_${rowCount}_monthly" class="form-control form-control-sm" step="0.01" oninput="updateLoanAmortizations()"></td>
        <td><button type="button" class="btn btn-sm btn-danger" onclick="removeLoanRow(this)"><i class="bi bi-trash"></i></button></td>
    `;
    container.appendChild(row);
}

// Remove loan row
function removeLoanRow(button) {
    button.closest('.loan-row').remove();
    updateLoanAmortizations();
}
