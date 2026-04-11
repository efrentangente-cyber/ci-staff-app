/* ============================================
   ENHANCED PROFESSIONAL SEARCH FUNCTIONALITY
   ============================================ */

// Toggle clear button visibility
function toggleClearButton(tableType) {
    const input = document.getElementById(`searchInput${tableType === 'pending' ? 'Pending' : tableType === 'processed' ? 'Processed' : tableType === 'completed' ? 'Completed' : 'Pending'}`);
    const wrapper = document.getElementById(`searchWrapper${tableType === 'pending' ? 'Pending' : tableType === 'processed' ? 'Processed' : tableType === 'completed' ? 'Completed' : 'Pending'}`);
    
    if (input && wrapper) {
        if (input.value.trim()) {
            wrapper.classList.add('has-value');
        } else {
            wrapper.classList.remove('has-value');
        }
    }
}

// Clear search
function clearSearch(tableType) {
    const inputId = tableType === 'pending' ? 'Pending' : tableType === 'processed' ? 'Processed' : tableType === 'completed' ? 'Completed' : 'Pending';
    const input = document.getElementById(`searchInput${inputId}`);
    
    if (input) {
        input.value = '';
        toggleClearButton(tableType);
        
        // Trigger search to reset table
        if (typeof searchApplications === 'function') {
            searchApplications(tableType);
        }
        
        input.focus();
    }
}

// Enhanced search with better UX
function enhancedSearch(tableType, tableId, countBadgeId) {
    const inputId = tableType === 'pending' ? 'Pending' : tableType === 'processed' ? 'Processed' : tableType === 'completed' ? 'Completed' : 'Pending';
    const searchValue = document.getElementById(`searchInput${inputId}`).value.toLowerCase().trim();
    const table = document.getElementById(tableId);
    
    if (!table) return;
    
    const tbody = table.getElementsByTagName('tbody')[0];
    if (!tbody) return;
    
    const rows = tbody.getElementsByTagName('tr');
    let visibleCount = 0;
    let noResultsRow = tbody.querySelector('.no-results-row');
    
    // Remove existing no results row
    if (noResultsRow) {
        noResultsRow.remove();
    }
    
    // Search through rows
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].classList.contains('no-results-row')) continue;
        
        const cells = rows[i].getElementsByTagName('td');
        let found = false;
        
        // Search through all cells
        for (let j = 0; j < cells.length; j++) {
            const cellText = cells[j].textContent.toLowerCase();
            if (cellText.includes(searchValue)) {
                found = true;
                break;
            }
        }
        
        if (found) {
            rows[i].style.display = '';
            visibleCount++;
        } else {
            rows[i].style.display = 'none';
        }
    }
    
    // Show "No results" message if nothing found
    if (visibleCount === 0 && searchValue) {
        const thead = table.querySelector('thead tr');
        const colCount = thead ? thead.cells.length : 1;
        const noResultsRow = tbody.insertRow();
        noResultsRow.className = 'no-results-row';
        const cell = noResultsRow.insertCell();
        cell.colSpan = colCount;
        cell.className = 'text-center text-muted py-5';
        cell.innerHTML = `
            <div style="font-size: 3rem; opacity: 0.3;">
                <i class="bi bi-search"></i>
            </div>
            <p class="mb-0 mt-2">No records found matching "<strong>${searchValue}</strong>"</p>
            <small>Try different keywords or clear the search</small>
        `;
    }
    
    // Update count badge
    const countBadge = document.getElementById(countBadgeId);
    if (countBadge) {
        if (searchValue) {
            countBadge.textContent = `${visibleCount} Found`;
            countBadge.className = 'badge bg-info';
        } else {
            const totalRows = Array.from(rows).filter(r => !r.classList.contains('no-results-row')).length;
            countBadge.textContent = `${totalRows} ${tableType === 'pending' ? 'Pending' : tableType === 'processed' ? 'Processed' : 'Completed'}`;
            countBadge.className = tableType === 'pending' ? 'badge bg-warning' : 'badge bg-success';
        }
    }
}
