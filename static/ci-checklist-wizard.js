// CI Checklist Wizard JavaScript

let currentPage = 1;
const totalPages = 6; // Updated to include Cash Flow page (2.5)
let checklistData = {};

// Initialize wizard
document.addEventListener('DOMContentLoaded', function() {
    loadSavedData();
    loadCheckboxData(); // Load checkbox data from summary page
    loadVerificationData(); // Load CI verification checkbox data
    updateProgressBar();
    setupAutoSave();
    setupComputationListeners();
    
    // Load Excel data if available
    setTimeout(() => {
        loadExcelData();
    }, 500); // Wait for Excel component to initialize
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


// OCR functionality removed - no longer needed

// Navigate to specific page
function goToPage(pageNumber) {
    // Convert to string to handle decimal pages like 2.5
    const pageStr = String(pageNumber);
    
    // Save current page data
    saveCurrentPageData();
    
    // If moving from page 2.5 (Excel) to page 3 (Computation), sync the data
    if (currentPage === 2.5 && pageNumber === 3) {
        syncExcelToComputation();
    }
    
    // Hide all pages
    document.querySelectorAll('.wizard-page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show target page
    const targetPage = document.querySelector(`.wizard-page[data-page="${pageStr}"]`);
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
    if (currentPage === 2.5) {
        goToPage(2);
    } else if (currentPage === 3) {
        goToPage(2.5);
    } else if (currentPage > 1) {
        goToPage(currentPage - 1);
    }
}

// Next page
function nextPage() {
    if (currentPage === 2) {
        goToPage(2.5);
    } else if (currentPage === 2.5) {
        goToPage(3);
    } else if (currentPage < 5) {
        goToPage(currentPage + 1);
    }
}

// Submit form
function submitChecklist() {
    saveCurrentPageData();
    
    // Get Excel spreadsheet data
    let excelData = null;
    if (window.excelSheet) {
        excelData = window.excelSheet.exportData();
    }
    
    // Add Excel data to checklist data
    checklistData.excel_cashflow = excelData;
    
    // Check if online
    if (!navigator.onLine) {
        // Save offline
        const signature = document.getElementById('ci_signature').value;
        const latitude = document.getElementById('ci_latitude').value;
        const longitude = document.getElementById('ci_longitude').value;
        const applicationId = parseInt(window.location.pathname.split('/').pop());
        
        syncManager.saveChecklistOffline(
            applicationId,
            checklistData,
            signature,
            latitude,
            longitude
        ).then(() => {
            alert('Checklist saved offline. Will upload when connection is available.');
            window.location.href = '/ci/dashboard';
        }).catch(err => {
            alert('Failed to save offline: ' + err.message);
        });
        
        return false;
    }
    
    // Online - submit normally
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
    updateOtherObligations(); // Trigger update of total expenses
}

function updateNewLoan() {
    const applied = getNumericValue('new_loan_amount');
    const deductible = getNumericValue('loan_deductible');
    const newLoan = applied - deductible;
    setComputedValue('new_loan_final', newLoan);
    updateOtherObligations(); // Trigger update of total expenses
}

function updateOtherObligations() {
    const household = getNumericValue('household_expenses');
    const tuition = getNumericValue('tuition');
    const medical = getNumericValue('medical');
    const water = getNumericValue('water_fuel');
    const internet = getNumericValue('internet');
    
    // Sum only the other obligations (not including loans)
    const otherObligationsOnly = household + tuition + medical + water + internet;
    
    // Get total loans (before new + new loan)
    const totalBeforeNew = getNumericValue('total_before_new');
    const newLoan = getNumericValue('new_loan_final');
    
    // TOTAL LOAN AMORTIZATIONS & OTHER OBLIGATIONS/EXPENSES = all loans + other obligations
    const totalWithLoans = totalBeforeNew + newLoan + otherObligationsOnly;
    setComputedValue('total_other_obligations', totalWithLoans);
    
    // Update final calculations after this
    updateFinalCalculations();
}

function updateFinalCalculations() {
    const totalIncome = getNumericValue('total_gross_income');
    const totalExpenses = getNumericValue('total_other_obligations'); // This now includes everything
    
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


// Load Excel data from saved checklist
function loadExcelData() {
    if (!window.excelSheet) {
        console.log('Excel sheet not initialized yet');
        return;
    }
    
    // Check if there's saved data in checklistData
    if (checklistData.excel_cashflow) {
        try {
            window.excelSheet.importData(checklistData.excel_cashflow);
            console.log('Excel data loaded from checklist');
        } catch (e) {
            console.error('Error loading Excel data:', e);
        }
    }
}

// Sync Excel Cash Flow data to Computation page (Page 2.5 -> Page 3)
function syncExcelToComputation() {
    if (!window.excelSheet) {
        console.log('Excel sheet not available for sync');
        return;
    }
    
    try {
        const cells = window.excelSheet.cells;
        
        // Extract key financial data from Excel spreadsheet
        // Look for common patterns in the templates
        
        // Try to find Total/Gross Sales or Total Income
        let totalIncome = 0;
        let netIncome = 0;
        
        // Search for cells containing income-related values
        Object.keys(cells).forEach(cellRef => {
            const cell = cells[cellRef];
            if (!cell) return;
            
            const value = cell.value ? cell.value.toString().toUpperCase() : '';
            const displayValue = parseFloat(cell.display) || 0;
            
            // Look for "GROSS PROFIT", "NET INCOME", "GROSS SALES"
            if (value.includes('GROSS PROFIT') || value.includes('NET MONTHLY INCOME') || value.includes('GROSS SALES')) {
                // Get the value from the next column (usually D column)
                const match = cellRef.match(/([A-Z]+)(\d+)/);
                if (match) {
                    const row = match[2];
                    const nextCol = 'D'; // Most templates use column D for amounts
                    const valueCell = cells[nextCol + row];
                    if (valueCell && valueCell.display) {
                        netIncome = Math.max(netIncome, parseFloat(valueCell.display) || 0);
                    }
                }
            }
            
            // Look for "TOTAL SALES" or "TOTAL MONTHLY INCOME"
            if (value.includes('TOTAL SALES') || value.includes('TOTAL MONTHLY INCOME')) {
                const match = cellRef.match(/([A-Z]+)(\d+)/);
                if (match) {
                    const row = match[2];
                    const nextCol = 'D';
                    const valueCell = cells[nextCol + row] || cells['C' + row];
                    if (valueCell && valueCell.display) {
                        totalIncome = Math.max(totalIncome, parseFloat(valueCell.display) || 0);
                    }
                }
            }
        });
        
        // Populate the computation page with extracted data
        if (netIncome > 0) {
            // Set as business income (from Cash Flow Statement)
            const businessIncomeInput = document.querySelector('[name="income_business"]');
            if (businessIncomeInput && !businessIncomeInput.value) {
                businessIncomeInput.value = netIncome.toFixed(2);
                
                // Show notification
                showSyncNotification(netIncome);
            }
        }
        
        // Trigger all computations
        updateAllComputations();
        
    } catch (e) {
        console.error('Error syncing Excel to Computation:', e);
    }
}

// Show sync notification
function showSyncNotification(amount) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        <h6><i class="bi bi-check-circle"></i> Cash Flow Data Synced!</h6>
        <p class="mb-0 small">Business income of ₱${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')} has been automatically filled from your Cash Flow Statement.</p>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Auto-save Excel data periodically (silently in background)
setInterval(() => {
    if (window.excelSheet && currentPage === 2.5) {
        const excelData = window.excelSheet.exportData();
        checklistData.excel_cashflow = excelData;
        sessionStorage.setItem('ci_checklist_data', JSON.stringify(checklistData));
        // Silent save - no notification or submission
    }
}, 10000); // Save every 10 seconds when on Excel page
