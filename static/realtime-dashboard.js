// Real-time Dashboard Updates with WebSocket Push
// Instant updates when new applications are submitted

let lastUpdateTime = Date.now();
let currentDashboard = null;
const lpsUserId = typeof window.__LPS_USER_ID === 'number' || typeof window.__LPS_USER_ID === 'string'
    ? parseInt(String(window.__LPS_USER_ID), 10)
    : null;
function lpsWantsThisSocketPayload(data) {
    if (currentDashboard !== 'loan' || lpsUserId == null || Number.isNaN(lpsUserId)) {
        return true;
    }
    if (!data || data.submitted_by == null) {
        return false;
    }
    return parseInt(String(data.submitted_by), 10) === lpsUserId;
}

// Detect which dashboard we're on
if (window.location.pathname.includes('/admin/dashboard')) {
    currentDashboard = 'admin';
} else if (window.location.pathname.includes('/loan/dashboard')) {
    currentDashboard = 'loan';
} else if (window.location.pathname.includes('/ci/dashboard')) {
    currentDashboard = 'ci';
}

// Use the single client from base.html (window.__dcccoSocket) — a second io() call doubled
// connections and could make the app feel slow / overload the server.
let refreshDebounce = null;
function scheduleRefreshApplications() {
    if (refreshDebounce) {
        clearTimeout(refreshDebounce);
    }
    refreshDebounce = setTimeout(function() {
        refreshDebounce = null;
        refreshApplications();
    }, 200);
}

function initDcccoDashboardRealtime() {
    if (initDcccoDashboardRealtime._done) {
        return;
    }
    const socket = window.__dcccoSocket;
    if (!socket || !currentDashboard) {
        return;
    }
    initDcccoDashboardRealtime._done = true;

    socket.on('connect', function() {
        if (hasApplicationsTableForPolling()) {
            scheduleRefreshApplications();
        }
    });

    socket.on('disconnect', function(reason) {
        if (reason === 'io server disconnect') {
            try {
                socket.connect();
            } catch (e) { /* ignore */ }
        }
    });

    socket.on('reconnect', function() {
        if (hasApplicationsTableForPolling()) {
            scheduleRefreshApplications();
        }
    });

    socket.on('new_application', function(data) {
        if (!lpsWantsThisSocketPayload(data)) {
            return;
        }
        showToast('New Application', `${data.member_name} submitted a loan application`, 'success');
        scheduleRefreshApplications();
    });

    socket.on('application_updated', function(data) {
        if (!lpsWantsThisSocketPayload(data)) {
            return;
        }
        const rawStatus = (data && data.status) ? data.status : 'Updated';
        const statusText = String(rawStatus).replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });
        showToast('Application Updated', `${data.member_name} - ${statusText}`, 'info');
        scheduleRefreshApplications();
    });
}

function hasApplicationsTableForPolling() {
    return !!document.querySelector('#applicationsTable tbody');
}

if (currentDashboard) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDcccoDashboardRealtime, { once: true });
    } else {
        initDcccoDashboardRealtime();
    }
}

// Toast notification function
function showToast(title, message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : type === 'info' ? 'info' : 'warning'} alert-dismissible fade show`;
    toast.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML = `
        <strong>${title}</strong><br>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function refreshApplications() {
    if (!currentDashboard) {
        return;
    }
    // No template currently defines #applicationsTable; polling it was hammering
    // the server every 2s for no UI benefit. Skip the API when there is no legacy table.
    if (!hasApplicationsTableForPolling()) {
        return;
    }

    const apiUrl = `/api/${currentDashboard}/applications`;

    fetch(apiUrl, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(applications => {
            updateApplicationsTable(applications);
            lastUpdateTime = Date.now();
        })
        .catch(error => console.error('Error fetching applications:', error));
}

function updateApplicationsTable(applications) {
    const tbody = document.querySelector('#applicationsTable tbody');
    if (!tbody) return;
    
    // Store current search and filter values
    const searchInput = document.getElementById('searchInput');
    const filterSelect = document.getElementById('statusFilter');
    const searchValue = searchInput ? searchInput.value : '';
    const filterValue = filterSelect ? filterSelect.value : 'all';
    
    tbody.innerHTML = '';
    
    applications.forEach(app => {
        const row = document.createElement('tr');
        
        // Format date (DD-MM-YY)
        const date = app.submitted_at.substring(8, 10) + '-' + 
                     app.submitted_at.substring(5, 7) + '-' + 
                     app.submitted_at.substring(2, 4);
        
        // Status badge color
        let badgeClass = 'warning';
        if (app.status === 'approved') badgeClass = 'success';
        else if (app.status === 'disapproved') badgeClass = 'danger';
        else if (app.status === 'ci_completed') badgeClass = 'info';
        
        // Build row based on dashboard type
        if (currentDashboard === 'admin') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td><strong>₱${parseFloat(app.loan_amount).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${app.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                </td>
                <td>${app.loan_staff_name || 'N/A'}</td>
                <td>${app.ci_staff_name || 'N/A'}</td>
                <td>${date}</td>
                <td>
                    <a href="/admin/application/${app.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i>
                        <span class="btn-text">Review</span>
                    </a>
                </td>
            `;
        } else if (currentDashboard === 'loan') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td><strong>₱${parseFloat(app.loan_amount).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${app.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                </td>
                <td>${app.ci_staff_name || 'N/A'}</td>
                <td>
                    <a href="/loan/application/${app.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i>
                        <span class="btn-text">View</span>
                    </a>
                </td>
            `;
        } else if (currentDashboard === 'ci') {
            const actionButton = app.status === 'ci_completed' 
                ? `<a href="/ci/application/${app.id}" class="btn btn-sm btn-success">
                       <i class="bi bi-eye"></i>
                       <span class="btn-text">View</span>
                   </a>`
                : `<a href="/ci/application/${app.id}" class="btn btn-sm btn-primary">
                       <i class="bi bi-pencil"></i>
                       <span class="btn-text">Start</span>
                   </a>`;
            
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td>${date}</td>
                <td>${app.member_address || 'N/A'}</td>
                <td>${actionButton}</td>
            `;
        }
        
        tbody.appendChild(row);
    });
    
    // Update stats if they exist
    updateDashboardStats(applications);
    
    // Reapply search and filter (legacy #applicationsTable + datatable.js only)
    if (searchValue && typeof dataTable !== 'undefined' && dataTable && searchInput) {
        searchInput.value = searchValue;
        if (typeof runDataTableSearch === 'function') runDataTableSearch();
    }
    if (filterValue !== 'all' && typeof dataTable !== 'undefined' && dataTable && filterSelect) {
        filterSelect.value = filterValue;
        if (typeof runDataTableFilter === 'function') runDataTableFilter();
    } else {
        const totalCount = document.getElementById('totalCount');
        if (totalCount) {
            totalCount.textContent = `${applications.length} Total`;
        }
    }
}

function updateDashboardStats(applications) {
    // Update stats based on dashboard type
    if (currentDashboard === 'admin') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const forReview = applications.filter(a => ['submitted', 'ci_completed'].includes(a.status)).length;
        const forReviewStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (forReviewStat) forReviewStat.textContent = forReview;
        
        const approved = applications.filter(a => a.status === 'approved').length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;
    } else if (currentDashboard === 'loan') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const pending = applications.filter(a => a.status === 'submitted').length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;
        
        const approved = applications.filter(a => a.status === 'approved').length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;
        
        const totalAmount = applications.reduce((sum, a) => sum + parseFloat(a.loan_amount || 0), 0);
        const amountStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
        if (amountStat) amountStat.textContent = '₱' + totalAmount.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
    } else if (currentDashboard === 'ci') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const pending = applications.filter(a => a.status !== 'ci_completed').length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;
        
        const completed = applications.filter(a => a.status === 'ci_completed').length;
        const completedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (completedStat) completedStat.textContent = completed;
    }
}

// Optional slow poll only if a legacy #applicationsTable exists (e.g. future admin view).
if (currentDashboard) {
    setInterval(function() {
        if (document.visibilityState === 'visible' && hasApplicationsTableForPolling() && (!window.__dcccoSocket || !window.__dcccoSocket.connected)) {
            refreshApplications();
        }
    }, 90000);
}
