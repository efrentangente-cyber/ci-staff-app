// CI Checklist Wizard JavaScript

let currentPage = 1;
const totalPages = 8;
let checklistData = {};

// Initialize wizard
document.addEventListener('DOMContentLoaded', function() {
    loadSavedData();
    updateProgressBar();
    setupAutoSave();
    setupComputationListeners();
});

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
    document.querySelectorAll('.progress-step').forEach((step, index) => {
        const stepNumber = index + 1;
        step.classList.remove('active', 'completed');
        
        if (stepNumber < currentPage) {
            step.classList.add('completed');
        } else if (stepNumber === currentPage) {
            step.classList.add('active');
        }
    });
    
    // Update page indicator
    const indicator = document.querySelector('.page-indicator');
    if (indicator) {
        indicator.textContent = `Page ${currentPage} of ${totalPages}`;
    }
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
