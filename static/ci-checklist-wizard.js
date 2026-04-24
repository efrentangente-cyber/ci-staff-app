// CI Checklist Wizard JavaScript

let currentPage = 1;
const totalPages = 6; // Updated to include Cash Flow page (2.5)
let checklistData = {};

function buildChecklistPayloadFromForm() {
    const form = document.getElementById('ciChecklistForm');
    if (!form) return {};

    const payload = {};
    const fields = form.querySelectorAll('input[name], select[name], textarea[name]');
    fields.forEach((field) => {
        if (!field.name || field.type === 'file') return;
        if (field.type === 'checkbox') {
            payload[field.name] = field.checked;
        } else if (field.type === 'radio') {
            if (field.checked) payload[field.name] = field.value;
            else if (!(field.name in payload)) payload[field.name] = '';
        } else {
            payload[field.name] = field.value;
        }
    });

    return payload;
}

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
    
    // Trigger initial computation when navigating to Page 3
    setTimeout(() => {
        if (currentPage === 3) {
            updateAllComputations();
        }
    }, 1000);
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
        
        // Trigger computations when navigating to Page 3
        if (pageNumber === 3) {
            setTimeout(() => {
                updateAllComputations();
            }, 100);
        }
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
    // Save full form state so DB gets complete payload (checkboxes optional).
    checklistData = buildChecklistPayloadFromForm();
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

    // Ensure hidden payload has full form state before submit.
    document.getElementById('checklist_data').value = JSON.stringify(checklistData);
    
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
    document.getElementById('ciChecklistForm').submit();
}

// Computation functions for Page 3
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
    
    // Loan fields
    const loanFields = ['dccco_loan_1', 'dccco_loan_2', 'new_loan_amount', 'loan_deductible'];
    loanFields.forEach(field => {
        const input = document.querySelector(`[name="${field}"]`);
        if (input) {
            input.addEventListener('input', updateAllComputations);
        }
    });
    
    // Other obligations fields
    const obligationFields = ['household_expenses', 'tuition', 'medical', 'water_fuel', 'internet'];
    obligationFields.forEach(field => {
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
    // Trigger the cascade of updates
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
    
    // Net Disposable Income = Total Gross Income - Total Expenses
    const netDisposable = totalIncome - totalExpenses;
    setComputedValue('net_disposable_income', netDisposable);
    
    if (totalIncome > 0) {
        // Debt & Expense Ratio = (Total Expenses / Total Gross Income) × 100
        const ratio = (totalExpenses / totalIncome) * 100;
        setComputedValue('debt_expense_ratio', ratio);
        
        // Loan Amortization Limit = Total Gross Income × 0.80
        const loanLimit = totalIncome * 0.80;
        setComputedValue('loan_amortization_limit', loanLimit);
    } else {
        setComputedValue('debt_expense_ratio', 0);
        setComputedValue('loan_amortization_limit', 0);
    }
}

function renumberLoanRows() {
    const container = document.getElementById('loan_rows_container');
    if (!container) return;
    const rows = Array.from(container.querySelectorAll('tr.loan-row'));
    rows.forEach((tr, idx) => {
        const n = idx + 1;
        tr.querySelectorAll('input[name^="loan_"]').forEach((input) => {
            const name = input.getAttribute('name');
            if (!name) return;
            const m = name.match(/^loan_\d+_(.+)$/);
            if (m) {
                input.setAttribute('name', `loan_${n}_${m[1]}`);
            }
        });
    });
    rows.forEach((tr) => {
        const del = tr.querySelector('button[onclick*="removeLoanRow"]');
        if (del) {
            del.disabled = rows.length <= 1;
        }
    });
}

function initLoanRowSelection() {
    const tb = document.getElementById('loan_rows_container');
    if (!tb) return;
    tb.addEventListener('click', (e) => {
        const tr = e.target.closest('tr.loan-row');
        if (!tr) return;
        if (e.target.closest('button')) return;
        tb.querySelectorAll('tr.loan-row').forEach((r) => r.classList.remove('loan-row--selected'));
        tr.classList.add('loan-row--selected');
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLoanRowSelection);
} else {
    initLoanRowSelection();
}

// Add dynamic loan row — inserted under the selected row (reindexes names)
function addLoanRow() {
    const container = document.getElementById('loan_rows_container');
    if (!container) return;
    const n = container.querySelectorAll('tr.loan-row').length + 1;
    const row = document.createElement('tr');
    row.className = 'loan-row';
    row.innerHTML = `
        <td><input type="text" name="loan_${n}_institution" class="form-control form-control-sm"></td>
        <td><input type="number" name="loan_${n}_principal" class="form-control form-control-sm" step="0.01" value="0" oninput="updateAllComputations()"></td>
        <td><input type="number" name="loan_${n}_balance" class="form-control form-control-sm" step="0.01" value="0" oninput="updateAllComputations()"></td>
        <td><input type="number" name="loan_${n}_monthly" class="form-control form-control-sm" step="0.01" value="0" oninput="updateAllComputations()"></td>
        <td class="text-center align-middle py-1"><button type="button" class="btn btn-sm btn-outline-secondary" onclick="removeLoanRow(this)" title="Remove row"><i class="bi bi-trash"></i></button></td>
    `;
    const selected = container.querySelector('tr.loan-row--selected');
    if (selected) {
        selected.insertAdjacentElement('afterend', row);
    } else {
        container.appendChild(row);
    }
    container.querySelectorAll('tr.loan-row').forEach((r) => r.classList.remove('loan-row--selected'));
    row.classList.add('loan-row--selected');
    renumberLoanRows();
    updateAllComputations();
}

// Remove loan row
function removeLoanRow(button) {
    const container = document.getElementById('loan_rows_container');
    if (!container) return;
    if (container.querySelectorAll('tr.loan-row').length <= 1) {
        return;
    }
    const tr = button.closest('tr.loan-row');
    const next = tr.nextElementSibling;
    tr.remove();
    renumberLoanRows();
    if (next && next.classList.contains('loan-row')) {
        next.classList.add('loan-row--selected');
    } else {
        const first = container.querySelector('tr.loan-row');
        if (first) first.classList.add('loan-row--selected');
    }
    updateAllComputations();
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

        const parseMoney = (value) => {
            if (value === null || value === undefined || value === '') return 0;
            const cleaned = String(value).replace(/[^\d.-]/g, '');
            const parsed = parseFloat(cleaned);
            return Number.isFinite(parsed) ? parsed : 0;
        };

        const columnToIndex = (colName) => {
            let index = 0;
            for (let i = 0; i < colName.length; i++) {
                index = index * 26 + (colName.charCodeAt(i) - 64);
            }
            return index - 1;
        };

        const indexToColumn = (index) => {
            let name = '';
            let n = index;
            while (n >= 0) {
                name = String.fromCharCode((n % 26) + 65) + name;
                n = Math.floor(n / 26) - 1;
            }
            return name;
        };

        const cellNumber = (cell) => {
            if (!cell) return 0;
            return parseMoney(
                cell.display !== undefined && cell.display !== null
                    ? cell.display
                    : cell.value
            );
        };

        const findAmountOnSameRow = (cellRef) => {
            const match = cellRef.match(/([A-Z]+)(\d+)/);
            if (!match) return 0;
            const startCol = columnToIndex(match[1]);
            const row = match[2];

            // Read the first computed/numeric amount to the right of the label.
            for (let col = startCol + 1; col < (window.excelSheet.cols || 15); col++) {
                const amount = cellNumber(cells[indexToColumn(col) + row]);
                if (amount !== 0) return amount;
            }
            return 0;
        };

        const setAutoSyncedValue = (name, amount) => {
            if (!amount || amount <= 0) return false;
            let updated = false;
            document.querySelectorAll(`[name="${name}"]`).forEach((input) => {
                const current = parseMoney(input.value);
                const previousSync = parseMoney(input.dataset.cashflowSyncedAmount);
                const canUpdate = current === 0 || (previousSync > 0 && current === previousSync);

                if (canUpdate) {
                    input.value = amount.toFixed(2);
                    input.dataset.cashflowSyncedAmount = amount.toFixed(2);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    updated = true;
                }
            });
            return updated;
        };

        let totalIncome = 0;
        let businessIncome = 0;

        Object.keys(cells).forEach(cellRef => {
            const cell = cells[cellRef];
            if (!cell) return;
            
            const value = cell.value ? cell.value.toString().toUpperCase() : '';
            
            // Prefer net result from cash flow; fall back to gross sales/income.
            if (
                value.includes('GROSS PROFIT') ||
                value.includes('NET MONTHLY INCOME') ||
                value.includes('NET INCOME') ||
                value.includes('GROSS SALES')
            ) {
                businessIncome = Math.max(businessIncome, findAmountOnSameRow(cellRef));
            }
            
            if (
                value.includes('TOTAL SALES') ||
                value.includes('TOTAL MONTHLY INCOME')
            ) {
                totalIncome = Math.max(totalIncome, findAmountOnSameRow(cellRef));
            }
        });

        const amountToSync = businessIncome || totalIncome;
        if (setAutoSyncedValue('income_business', amountToSync)) {
            showSyncNotification(amountToSync);
        }
        
        // Trigger all computations
        updateAllComputations();
        saveCurrentPageData();
        
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
