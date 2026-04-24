// Professional DataTable Implementation
class DataTable {
    constructor(tableId, options = {}) {
        this.table = document.getElementById(tableId);
        this.tbody = this.table.querySelector('tbody');
        this.thead = this.table.querySelector('thead');
        this.rows = Array.from(this.tbody.querySelectorAll('tr'));
        this.currentPage = 1;
        this.rowsPerPage = options.rowsPerPage || 15;
        this.sortColumn = -1;
        this.sortAsc = true;
        this.searchValue = '';
        this.filterValue = 'all';
        
        this.init();
    }
    
    init() {
        this.makeHeadersSortable();
        this.renderPagination();
        this.showPage(1);
    }
    
    makeHeadersSortable() {
        const headers = this.thead.querySelectorAll('th');
        headers.forEach((header, index) => {
            if (index < headers.length - 1) { // Don't make Actions column sortable
                header.style.cursor = 'pointer';
                header.style.userSelect = 'none';
                header.innerHTML += ' <i class="bi bi-arrow-down-up sort-icon"></i>';
                
                header.addEventListener('click', () => {
                    this.sortByColumn(index);
                });
            }
        });
    }
    
    sortByColumn(columnIndex) {
        if (this.sortColumn === columnIndex) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortColumn = columnIndex;
            this.sortAsc = true;
        }
        
        // Update sort icons
        const headers = this.thead.querySelectorAll('th');
        headers.forEach((header, index) => {
            const icon = header.querySelector('.sort-icon');
            if (icon) {
                if (index === columnIndex) {
                    icon.className = this.sortAsc ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
                } else {
                    icon.className = 'bi bi-arrow-down-up sort-icon';
                }
            }
        });
        
        // Sort rows
        this.rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent.trim();
            const bValue = b.cells[columnIndex].textContent.trim();
            
            // Try to parse as number
            const aNum = parseFloat(aValue.replace(/[₱,]/g, ''));
            const bNum = parseFloat(bValue.replace(/[₱,]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.sortAsc ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            return this.sortAsc ? 
                aValue.localeCompare(bValue) : 
                bValue.localeCompare(aValue);
        });
        
        this.showPage(this.currentPage);
    }
    
    search(searchValue) {
        this.searchValue = (searchValue == null ? '' : String(searchValue)).toLowerCase().trim();
        this.currentPage = 1;
        this.showPage(1);
    }
    
    filter(filterValue) {
        this.filterValue = filterValue;
        this.currentPage = 1;
        this.showPage(1);
    }
    
    getVisibleRows() {
        return this.rows.filter(row => {
            // Search filter
            if (this.searchValue) {
                const text = row.textContent.toLowerCase();
                if (!text.includes(this.searchValue)) {
                    return false;
                }
            }
            
            // Status filter
            if (this.filterValue && this.filterValue !== 'all') {
                const statusCell = row.cells[3]; // Assuming status is 4th column
                if (statusCell) {
                    const badge = statusCell.querySelector('.badge');
                    const select = statusCell.querySelector('select');
                    
                    if (badge) {
                        const statusText = badge.textContent.trim().toLowerCase();
                        const filterText = this.filterValue.replace('_', ' ').toLowerCase();
                        if (statusText !== filterText) {
                            return false;
                        }
                    } else if (select) {
                        if (select.value !== this.filterValue) {
                            return false;
                        }
                    }
                }
            }
            
            return true;
        });
    }
    
    showPage(pageNum) {
        const visibleRows = this.getVisibleRows();
        const totalPages = Math.ceil(visibleRows.length / this.rowsPerPage);
        this.currentPage = Math.max(1, Math.min(pageNum, totalPages));
        
        const start = (this.currentPage - 1) * this.rowsPerPage;
        const end = start + this.rowsPerPage;
        
        // Hide all rows first
        this.rows.forEach(row => row.style.display = 'none');
        
        // Show only visible rows for current page
        visibleRows.forEach((row, index) => {
            if (index >= start && index < end) {
                row.style.display = '';
            }
        });
        
        // Clear and re-append rows in sorted order
        this.tbody.innerHTML = '';
        this.rows.forEach(row => this.tbody.appendChild(row));
        
        this.updatePagination(visibleRows.length, totalPages);
        this.updateCount(visibleRows.length);
    }
    
    renderPagination() {
        const paginationContainer = document.createElement('div');
        paginationContainer.id = 'paginationContainer';
        paginationContainer.className = 'pagination-container';
        
        this.table.parentElement.appendChild(paginationContainer);
    }
    
    updatePagination(totalRows, totalPages) {
        const container = document.getElementById('paginationContainer');
        if (!container) return;
        
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '<nav><ul class="pagination pagination-sm justify-content-center mb-0">';
        
        // Previous button
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="dataTable.showPage(${this.currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>`;
        
        // Page numbers
        const maxButtons = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxButtons / 2));
        let endPage = Math.min(totalPages, startPage + maxButtons - 1);
        
        if (endPage - startPage < maxButtons - 1) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }
        
        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="dataTable.showPage(1); return false;">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="dataTable.showPage(${i}); return false;">${i}</a>
            </li>`;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" onclick="dataTable.showPage(${totalPages}); return false;">${totalPages}</a></li>`;
        }
        
        // Next button
        html += `<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="dataTable.showPage(${this.currentPage + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>`;
        
        html += '</ul></nav>';
        
        // Add info text
        const start = (this.currentPage - 1) * this.rowsPerPage + 1;
        const end = Math.min(this.currentPage * this.rowsPerPage, totalRows);
        html += `<div class="pagination-info">Showing ${start}-${end} of ${totalRows}</div>`;
        
        container.innerHTML = html;
    }
    
    updateCount(visibleCount) {
        const countBadge = document.getElementById('totalCount');
        if (countBadge) {
            const suffix = this.searchValue ? 'Found' : this.filterValue !== 'all' ? 'Filtered' : 'Total';
            countBadge.textContent = `${visibleCount} ${suffix}`;
        }
    }
}

// Global instance
let dataTable;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const applicationsTable = document.getElementById('applicationsTable');
    if (applicationsTable) {
        dataTable = new DataTable('applicationsTable', { rowsPerPage: 15 });
    }
});

// Search function
function searchApplications(query) {
    const searchInput = document.getElementById('searchInput');
    const searchValue = (searchInput ? searchInput.value : (query || '')) || '';
    if (dataTable) {
        dataTable.search(searchValue);
    }
}

// Filter function
function filterApplications() {
    const filterSelect = document.getElementById('statusFilter');
    const filterValue = filterSelect ? filterSelect.value : 'all';
    if (dataTable) {
        dataTable.filter(filterValue);
    }
}
