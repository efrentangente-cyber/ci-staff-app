// Real-time Dashboard Updates with WebSocket Push — refreshes matching dashboard DOM

let lastUpdateTime = Date.now();
let currentDashboard = null;
const lpsUserId = typeof window.__LPS_USER_ID === 'number' || typeof window.__LPS_USER_ID === 'string'
    ? parseInt(String(window.__LPS_USER_ID), 10)
    : null;

function escapeHtml(s) {
    if (s == null || s === '') return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

function formatSubmittedSlash(val) {
    if (!val) return '';
    const d = val instanceof Date ? val : new Date(val);
    if (!Number.isNaN(d.getTime())) {
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyy = d.getFullYear();
        return `${dd}/${mm}/${yyyy}`;
    }
    const str = String(val);
    if (str.length >= 10 && str[4] === '-' && str[7] === '-') {
        return `${str.slice(8, 10)}/${str.slice(5, 7)}/${str.slice(0, 4)}`;
    }
    return str;
}

function formatSubmittedShort(val) {
    if (!val) return '';
    const d = val instanceof Date ? val : new Date(val);
    if (!Number.isNaN(d.getTime())) {
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yy = String(d.getFullYear()).slice(-2);
        return `${dd}-${mm}-${yy}`;
    }
    const str = String(val);
    if (str.length >= 10 && str[4] === '-' && str[7] === '-') {
        return `${str.slice(8, 10)}-${str.slice(5, 7)}-${str.slice(2, 4)}`;
    }
    return str;
}

function formatMoneyPhp(amount) {
    const n = parseFloat(amount);
    if (Number.isNaN(n)) return '₱0.00';
    return '₱' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function lpsWantsThisSocketPayload(data) {
    if (currentDashboard !== 'loan' || lpsUserId == null || Number.isNaN(lpsUserId)) {
        return true;
    }
    if (!data || data.submitted_by == null) {
        return false;
    }
    return parseInt(String(data.submitted_by), 10) === lpsUserId;
}

if (window.location.pathname.includes('/admin/dashboard')) {
    currentDashboard = 'admin';
} else if (window.location.pathname.includes('/loan/dashboard')) {
    currentDashboard = 'loan';
} else if (window.location.pathname.includes('/ci/dashboard')) {
    currentDashboard = 'ci';
}

let refreshDebounce = null;

function scheduleRefreshApplications(immediate) {
    if (immediate) {
        if (refreshDebounce) {
            clearTimeout(refreshDebounce);
            refreshDebounce = null;
        }
        requestAnimationFrame(function () {
            refreshApplications();
        });
        return;
    }
    if (refreshDebounce) {
        clearTimeout(refreshDebounce);
    }
    refreshDebounce = setTimeout(function () {
        refreshDebounce = null;
        refreshApplications();
    }, 50);
}

function hasLegacyApplicationsTable() {
    return !!document.querySelector('#applicationsTable tbody');
}

function hasLoanDashboardTables() {
    return !!document.getElementById('pendingTableBody');
}

function hasCiDashboardTables() {
    return currentDashboard === 'ci' && !!document.getElementById('completedTable');
}

function hasAdminDashboardTables() {
    return currentDashboard === 'admin' && !!document.getElementById('inProcessTable');
}

function needsApplicationListRefresh() {
    return hasLegacyApplicationsTable() || hasLoanDashboardTables() || hasCiDashboardTables() || hasAdminDashboardTables();
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

    socket.on('connect', function () {
        if (needsApplicationListRefresh()) {
            scheduleRefreshApplications(true);
        }
    });

    socket.on('disconnect', function (reason) {
        if (reason === 'io server disconnect') {
            try {
                socket.connect();
            } catch (e) { /* ignore */ }
        }
    });

    socket.on('reconnect', function () {
        if (needsApplicationListRefresh()) {
            scheduleRefreshApplications(true);
        }
    });

    socket.on('new_application', function (data) {
        if (!lpsWantsThisSocketPayload(data)) {
            return;
        }
        const name = (data && data.member_name) ? String(data.member_name) : 'Member';
        showToast('New Application', `${name} submitted a loan application`, 'success');
        scheduleRefreshApplications(true);
    });

    socket.on('application_updated', function (data) {
        if (!lpsWantsThisSocketPayload(data)) {
            return;
        }
        const rawStatus = (data && data.status) ? data.status : 'Updated';
        const statusText = String(rawStatus).replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); });
        const name = (data && data.member_name) ? String(data.member_name) : 'Application';
        showToast('Application Updated', `${name} — ${statusText}`, 'info');
        scheduleRefreshApplications(true);
    });
}

if (currentDashboard) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDcccoDashboardRealtime, { once: true });
    } else {
        initDcccoDashboardRealtime();
    }
}

function showToast(title, message, type) {
    type = type || 'info';
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : type === 'info' ? 'info' : 'warning'} alert-dismissible fade show`;
    toast.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML = `
        <strong>${escapeHtml(title)}</strong><br>
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(toast);

    setTimeout(function () {
        toast.remove();
    }, 5000);
}

function refreshApplications() {
    if (!currentDashboard) {
        return;
    }
    if (hasLoanDashboardTables()) {
        fetchJsonArray('/api/loan/applications', function (applications) {
            renderLoanDashboardTables(applications);
            lastUpdateTime = Date.now();
        });
        return;
    }
    if (hasCiDashboardTables()) {
        fetchJsonArray('/api/ci/applications', function (applications) {
            renderCiDashboardTables(applications);
            lastUpdateTime = Date.now();
        });
        return;
    }
    if (hasAdminDashboardTables()) {
        fetch('/api/admin/applications', { credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok) throw new Error('admin applications');
                return r.json();
            })
            .then(function (payload) {
                if (!payload || !Array.isArray(payload.applications) || !Array.isArray(payload.in_process_applications)) {
                    throw new Error('bad snapshot shape');
                }
                renderAdminDashboardTables(payload.applications, payload.in_process_applications);
                lastUpdateTime = Date.now();
            })
            .catch(function (err) {
                console.error('Error fetching admin dashboard snapshot:', err);
            });
        return;
    }
    if (!hasLegacyApplicationsTable()) {
        return;
    }

    fetchJsonArray(`/api/${currentDashboard}/applications`, function (applications) {
        updateApplicationsTable(applications);
        lastUpdateTime = Date.now();
    });
}

function fetchJsonArray(url, onOk) {
    fetch(url, { credentials: 'same-origin' })
        .then(function (response) {
            if (!response.ok) throw new Error(response.statusText);
            return response.json();
        })
        .then(function (data) {
            if (!Array.isArray(data)) {
                throw new Error('expected array');
            }
            onOk(data);
        })
        .catch(function (error) {
            console.error('Error fetching applications:', error);
        });
}

function renderLoanDashboardTables(applications) {
    const pendingBody = document.getElementById('pendingTableBody');
    const processedBody = document.getElementById('processedTableBody');
    if (!pendingBody || !processedBody) return;

    const PENDING_STATUSES = ['submitted', 'assigned_to_ci', 'ci_completed'];
    const pendingApps = applications.filter(function (a) {
        return PENDING_STATUSES.indexOf(a.status) >= 0;
    });

    function statusCellHtml(app) {
        if (app.status === 'ci_completed') {
            return '<span class="badge bg-info">CI Completed</span>';
        }
        if (app.status === 'assigned_to_ci') {
            return '<span class="badge bg-warning">Assigned to CI</span>';
        }
        return '<span class="badge bg-secondary">Submitted</span>';
    }

    function ciCellHtml(app) {
        if (app.assigned_ci_staff) {
            return '<span class="badge bg-primary">' + escapeHtml(app.ci_staff_name || 'CI') + '</span>';
        }
        return '<span class="text-muted">Not Assigned</span>';
    }

    pendingBody.innerHTML = '';
    pendingApps.forEach(function (app) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
            <td>${statusCellHtml(app)}</td>
            <td>${ciCellHtml(app)}</td>
            <td><span class="date-display">${escapeHtml(formatSubmittedSlash(app.submitted_at))}</span></td>
            <td>
                <a href="/loan/application/${app.id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-eye"></i>
                    <span class="d-none d-md-inline">View</span>
                </a>
            </td>
        `;
        pendingBody.appendChild(tr);
    });

    function isProcessedStatus(st) {
        return st === 'approved' || st === 'rejected' || st === 'disapproved';
    }
    const processedApps = applications.filter(function (a) {
        return isProcessedStatus(a.status);
    });

    processedBody.innerHTML = '';
    processedApps.forEach(function (app) {
        const tr = document.createElement('tr');
        let badge;
        if (app.status === 'approved') {
            badge = '<span class="badge bg-success">Approved</span>';
        } else {
            badge = '<span class="badge bg-danger">Rejected</span>';
        }
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
            <td>${badge}</td>
            <td>${ciCellHtml(app)}</td>
            <td><span class="date-display">${escapeHtml(formatSubmittedSlash(app.submitted_at))}</span></td>
            <td>
                <a href="/loan/application/${app.id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-eye"></i>
                    <span class="d-none d-md-inline">View</span>
                </a>
            </td>
        `;
        processedBody.appendChild(tr);
    });

    const pendingForStat = applications.filter(function (a) {
        return a.status === 'submitted' || a.status === 'assigned_to_ci';
    }).length;
    const approvedCount = applications.filter(function (a) { return a.status === 'approved'; }).length;
    const totalStat = document.querySelector('.stat-card.blue h3');
    if (totalStat) totalStat.textContent = applications.length;
    const pendingStatCard = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
    if (pendingStatCard) pendingStatCard.textContent = pendingForStat;
    const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
    if (approvedStat) approvedStat.textContent = approvedCount;
    const successStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
    if (successStat) {
        const rate = applications.length > 0 ? (approvedCount / applications.length * 10) : 0;
        successStat.textContent = rate.toFixed(1);
    }

    const pc = document.getElementById('pendingCount');
    if (pc) {
        pc.textContent = applications.filter(function (a) {
            return PENDING_STATUSES.indexOf(a.status) >= 0;
        }).length + ' Pending';
    }
    const prc = document.getElementById('processedCount');
    if (prc) {
        prc.textContent = processedApps.length + ' Processed';
    }

    try {
        if (typeof searchApplications === 'function') {
            searchApplications('pending');
            searchApplications('processed');
        }
    } catch (e) { /* ignore */ }
}

function renderCiDashboardTables(applications) {
    const pendingTable = document.getElementById('pendingTable');
    const completedTable = document.getElementById('completedTable');
    if (!pendingTable || !completedTable) return;
    const pendingTbody = pendingTable.getElementsByTagName('tbody')[0];
    const completedTbody = completedTable.getElementsByTagName('tbody')[0];
    if (!pendingTbody || !completedTbody) return;

    const pendingApps = applications.filter(function (a) { return a.status === 'assigned_to_ci'; });
    const completedApps = applications.filter(function (a) { return a.status === 'ci_completed'; });

    pendingTbody.innerHTML = '';
    pendingApps.forEach(function (app) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td>${escapeHtml(formatSubmittedShort(app.submitted_at))}</td>
            <td>${escapeHtml(app.member_address || '')}</td>
            <td>
                <a href="/ci/review/${app.id}" class="btn btn-sm btn-warning">
                    <i class="bi bi-eye"></i>
                    <span class="btn-text">Start</span>
                </a>
                <button class="btn btn-sm btn-primary" onclick="syncManager.downloadApplication(${app.id})" title="Download for offline">
                    <i class="bi bi-download"></i>
                </button>
            </td>
        `;
        pendingTbody.appendChild(tr);
    });

    completedTbody.innerHTML = '';
    completedApps.forEach(function (app) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td>${escapeHtml(formatSubmittedShort(app.submitted_at))}</td>
            <td>${escapeHtml(app.member_address || '')}</td>
            <td>
                <a href="/ci/application/${app.id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-eye"></i>
                    <span class="btn-text">View</span>
                </a>
            </td>
        `;
        completedTbody.appendChild(tr);
    });

    const total = document.getElementById('ciStatTotal');
    const pend = document.getElementById('ciStatPending');
    const comp = document.getElementById('ciStatCompleted');
    const rate = document.getElementById('ciStatRate');
    if (total) total.textContent = applications.length;
    if (pend) pend.textContent = pendingApps.length;
    if (comp) comp.textContent = completedApps.length;
    if (rate) {
        const pct = applications.length > 0 ? Math.round(completedApps.length / applications.length * 100) : 0;
        rate.textContent = pct + '%';
    }

    const pBadge = document.getElementById('pendingCount');
    if (pBadge) pBadge.textContent = pendingApps.length + ' Pending';
    const cBadge = document.getElementById('completedCount');
    if (cBadge) cBadge.textContent = completedApps.length + ' Completed';

    try {
        if (typeof searchApplications === 'function') {
            searchApplications('pending');
            searchApplications('completed');
        }
    } catch (e) { /* ignore */ }
}

function adminForReview(app) {
    if (app.status === 'ci_completed') return true;
    const needs = Number(app.needs_ci_interview);
    return needs === 0 && app.status === 'submitted';
}

function renderAdminDashboardTables(applications, inProcess) {
    const pendingTable = document.getElementById('pendingTable');
    const processedTable = document.getElementById('processedTable');
    const inProcessTable = document.getElementById('inProcessTable');
    if (!pendingTable || !processedTable || !inProcessTable) return;

    const pendingTbody = pendingTable.getElementsByTagName('tbody')[0];
    const processedTbody = processedTable.getElementsByTagName('tbody')[0];
    const inProcessTbody = inProcessTable.getElementsByTagName('tbody')[0];
    if (!pendingTbody || !processedTbody || !inProcessTbody) return;

    const forReview = applications.filter(adminForReview);
    const processed = applications.filter(function (a) {
        return ['approved', 'disapproved', 'deferred'].indexOf(a.status) >= 0;
    });

    function reviewStatusBadge(app) {
        return '<span class="badge bg-warning">' +
            escapeHtml(String(app.status || '').replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); })) +
            '</span>';
    }

    pendingTbody.innerHTML = '';
    forReview.forEach(function (app) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
            <td>${reviewStatusBadge(app)}</td>
            <td>${escapeHtml(app.loan_staff_name || '')}</td>
            <td>${escapeHtml(app.ci_staff_name || 'N/A')}</td>
            <td>${escapeHtml(formatSubmittedShort(app.submitted_at))}</td>
            <td>
                <a href="/admin/application/${app.id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-eye"></i>
                    <span class="btn-text">Review</span>
                </a>
            </td>
        `;
        pendingTbody.appendChild(tr);
    });

    processedTbody.innerHTML = '';
    processed.forEach(function (app) {
        let badgeClass = 'danger';
        if (app.status === 'approved') badgeClass = 'success';
        else if (app.status === 'deferred') badgeClass = 'warning';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
            <td>
                <span class="badge bg-${badgeClass}">
                    ${escapeHtml(String(app.status || '').replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); }))}
                </span>
            </td>
            <td>${escapeHtml(app.loan_staff_name || '')}</td>
            <td>${escapeHtml(app.ci_staff_name || 'N/A')}</td>
            <td>${escapeHtml(formatSubmittedShort(app.submitted_at))}</td>
            <td>
                <a href="/admin/application/${app.id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-eye"></i>
                    <span class="btn-text">View</span>
                </a>
            </td>
        `;
        processedTbody.appendChild(tr);
    });

    inProcessTbody.innerHTML = '';
    inProcess.forEach(function (app) {
        const tr = document.createElement('tr');
        const badgeClass = app.status === 'submitted' ? 'secondary' : 'info';
        const ciArg = app.assigned_ci_staff != null ? app.assigned_ci_staff : null;
        tr.innerHTML = `
            <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name || '')}</td>
            <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
            <td>
                <span class="badge bg-${badgeClass}">
                    ${escapeHtml(String(app.status || '').replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); }))}
                </span>
            </td>
            <td>${escapeHtml(app.loan_staff_name || '')}</td>
            <td>${escapeHtml(app.ci_staff_name || 'Not Assigned')}</td>
            <td>${escapeHtml(formatSubmittedShort(app.submitted_at))}</td>
            <td>
                <button type="button" class="btn btn-sm btn-warning" onclick="openReassignModal(${app.id}, ${JSON.stringify(String(app.member_name || ''))}, ${ciArg})">
                    <i class="bi bi-arrow-repeat"></i>
                    <span class="btn-text">Reassign CI</span>
                </button>
            </td>
        `;
        inProcessTbody.appendChild(tr);
    });

    const totalStat = document.querySelector('.stat-card.blue h3');
    if (totalStat) totalStat.textContent = applications.length + inProcess.length;

    const forReviewCount = applications.filter(function (a) {
        return a.status === 'ci_completed' ||
            (Number(a.needs_ci_interview) === 0 && a.status === 'submitted');
    }).length;
    const forReviewStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
    if (forReviewStat) forReviewStat.textContent = forReviewCount;

    const inProcStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
    if (inProcStat) inProcStat.textContent = inProcess.length;

    const approvedStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
    if (approvedStat) approvedStat.textContent = applications.filter(function (a) { return a.status === 'approved'; }).length;

    const pBadge = document.getElementById('pendingCount');
    if (pBadge) pBadge.textContent = forReview.length + ' For Review';
    const procBadge = document.getElementById('processedCount');
    if (procBadge) procBadge.textContent = processed.length + ' Processed';
    const ipBadge = document.getElementById('inProcessCount');
    if (ipBadge) ipBadge.textContent = inProcess.length + ' In Process';

    try {
        if (typeof searchApplications === 'function') {
            searchApplications('pending');
            searchApplications('processed');
            searchApplications('inprocess');
        }
        if (typeof filterProcessed === 'function') {
            filterProcessed();
        }
    } catch (e) { /* ignore */ }
}

function updateApplicationsTable(applications) {
    const tbody = document.querySelector('#applicationsTable tbody');
    if (!tbody) return;

    const searchInput = document.getElementById('searchInput');
    const filterSelect = document.getElementById('statusFilter');
    const searchValue = searchInput ? searchInput.value : '';
    const filterValue = filterSelect ? filterSelect.value : 'all';

    tbody.innerHTML = '';

    applications.forEach(function (app) {
        const row = document.createElement('tr');

        let date = '';
        if (app.submitted_at && typeof app.submitted_at === 'string' && app.submitted_at.length >= 10) {
            date = app.submitted_at.substring(8, 10) + '-' +
                app.submitted_at.substring(5, 7) + '-' +
                app.submitted_at.substring(2, 4);
        } else {
            date = formatSubmittedShort(app.submitted_at);
        }

        let badgeClass = 'warning';
        if (app.status === 'approved') badgeClass = 'success';
        else if (app.status === 'disapproved' || app.status === 'rejected') badgeClass = 'danger';
        else if (app.status === 'ci_completed') badgeClass = 'info';

        if (currentDashboard === 'admin') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name)}</td>
                <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${escapeHtml(String(app.status || '').replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); }))}
                    </span>
                </td>
                <td>${escapeHtml(app.loan_staff_name || 'N/A')}</td>
                <td>${escapeHtml(app.ci_staff_name || 'N/A')}</td>
                <td>${escapeHtml(date)}</td>
                <td>
                    <a href="/admin/application/${app.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i>
                        <span class="btn-text">Review</span>
                    </a>
                </td>
            `;
        } else if (currentDashboard === 'loan') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name)}</td>
                <td><strong>${formatMoneyPhp(app.loan_amount)}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${escapeHtml(String(app.status || '').replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); }))}
                    </span>
                </td>
                <td>${escapeHtml(app.ci_staff_name || 'N/A')}</td>
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
                : `<a href="/ci/review/${app.id}" class="btn btn-sm btn-primary">
                       <i class="bi bi-pencil"></i>
                       <span class="btn-text">Start</span>
                   </a>`;

            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${escapeHtml(app.member_name)}</td>
                <td>${escapeHtml(date)}</td>
                <td>${escapeHtml(app.member_address || 'N/A')}</td>
                <td>${actionButton}</td>
            `;
        }

        tbody.appendChild(row);
    });

    updateDashboardStats(applications);

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
            totalCount.textContent = applications.length + ' Total';
        }
    }
}

function updateDashboardStats(applications) {
    if (currentDashboard === 'admin') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;

        const forReview = applications.filter(function (a) {
            return ['submitted', 'ci_completed'].indexOf(a.status) >= 0;
        }).length;
        const forReviewStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (forReviewStat) forReviewStat.textContent = forReview;

        const approved = applications.filter(function (a) { return a.status === 'approved'; }).length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;
    } else if (currentDashboard === 'loan') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;

        const pending = applications.filter(function (a) {
            return a.status === 'submitted' || a.status === 'assigned_to_ci';
        }).length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;

        const approved = applications.filter(function (a) { return a.status === 'approved'; }).length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;

        const rate = applications.length > 0
            ? (approved / applications.length * 10)
            : 0;
        const amountStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
        if (amountStat) amountStat.textContent = rate.toFixed(1);
    } else if (currentDashboard === 'ci') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;

        const pending = applications.filter(function (a) { return a.status !== 'ci_completed'; }).length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;

        const completed = applications.filter(function (a) { return a.status === 'ci_completed'; }).length;
        const completedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (completedStat) completedStat.textContent = completed;
    }
}

if (currentDashboard) {
    setInterval(function () {
        if (document.visibilityState === 'visible' && needsApplicationListRefresh() &&
            (!window.__dcccoSocket || !window.__dcccoSocket.connected)) {
            refreshApplications();
        }
    }, 90000);
}
