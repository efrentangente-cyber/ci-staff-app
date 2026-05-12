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

function memberHistoryHref(memberName, memberUid) {
    const base = typeof window.__MEMBER_HISTORY_URL === 'string' ? window.__MEMBER_HISTORY_URL : '/loan/member';
    const mu = memberUid != null && memberUid !== '' ? String(memberUid).trim() : '';
    const next = typeof window.location !== 'undefined' && window.location.pathname
        ? '&next=' + encodeURIComponent(window.location.pathname + window.location.search)
        : '';
    if (mu !== '' && /^\d+$/.test(mu)) {
        return base + '?member_uid=' + encodeURIComponent(mu) + next;
    }
    return base + '?name=' + encodeURIComponent(memberName || '') + next;
}

function groupLpsDashboardByMember(appList) {
    const buckets = {};
    const order = [];
    appList.forEach(function (app) {
        let key = null;
        const rawUid = app.member_uid;
        if (rawUid != null && String(rawUid).trim() !== '') {
            const n = parseInt(String(rawUid).trim(), 10);
            if (!Number.isNaN(n)) {
                key = 'uid:' + n;
            }
        }
        if (!key) {
            key = 'name:' + String(app.member_name || '').trim().toLowerCase();
        }
        if (!buckets[key]) {
            buckets[key] = {
                member_name: String(app.member_name || '').trim(),
                member_uid: rawUid != null && String(rawUid).trim() !== '' ? rawUid : null,
                apps: [],
            };
            order.push(key);
        } else {
            if (
                (buckets[key].member_uid == null || buckets[key].member_uid === '') &&
                rawUid != null &&
                String(rawUid).trim() !== ''
            ) {
                buckets[key].member_uid = rawUid;
            }
            const nm = String(app.member_name || '').trim();
            if (nm) {
                buckets[key].member_name = nm;
            }
        }
        buckets[key].apps.push(app);
    });
    return order.map(function (k) {
        return buckets[k];
    });
}

function stackedDashboardDivs(apps, mapFn) {
    return apps
        .map(function (a) {
            return '<div class="mb-1">' + mapFn(a) + '</div>';
        })
        .join('');
}

function formatMemberUidCell(mu) {
    if (mu == null || mu === '') {
        return '<span class="text-muted">—</span>';
    }
    return '<span class="text-nowrap">' + escapeHtml(String(mu)) + '</span>';
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
    }, 300);
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
    const ciCompletedBody = document.getElementById('ciCompletedTableBody');
    const processedBody = document.getElementById('processedTableBody');
    if (!pendingBody || !processedBody) return;

    function pipelineStatusHtml(app) {
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

    function stackedDivsHtml(apps, mapFn) {
        return apps.map(function (a) {
            return '<div class="mb-1">' + mapFn(a) + '</div>';
        }).join('');
    }

    function stackedAmountsHtml(apps) {
        return stackedDivsHtml(apps, function (a) {
            const lt = a.loan_type
                ? ' <span class="text-muted">' + escapeHtml(String(a.loan_type)) + '</span>'
                : '';
            return '<strong>' + formatMoneyPhp(a.loan_amount) + '</strong>' + lt;
        });
    }

    function memberNameLinkCellHtml(memberName, memberUid) {
        const href = memberHistoryHref(memberName, memberUid);
        return '<a href="' + href + '">' + escapeHtml(String(memberName || '')) + '</a>';
    }

    function viewButtonsColumnHtml(apps) {
        const btns = apps.map(function (a) {
            return (
                '<a href="/loan/application/' +
                a.id +
                '" class="btn btn-sm btn-primary">' +
                '<i class="bi bi-eye"></i>' +
                '<span class="d-none d-md-inline">View</span>' +
                '</a>'
            );
        }).join('');
        return '<div class="d-flex flex-column gap-1 align-items-start">' + btns + '</div>';
    }

    const pipelineApps = applications.filter(function (a) {
        return a.status === 'submitted' || a.status === 'assigned_to_ci';
    });
    const pipelineGroups = groupLpsDashboardByMember(pipelineApps);

    pendingBody.innerHTML = '';
    pipelineGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td>' +
            memberNameLinkCellHtml(g.member_name, g.member_uid) +
            '</td>' +
            '<td class="small">' +
            stackedAmountsHtml(g.apps) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, pipelineStatusHtml) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, ciCellHtml) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, function (a) {
                return '<span class="date-display">' + escapeHtml(formatSubmittedSlash(a.submitted_at)) + '</span>';
            }) +
            '</td>' +
            '<td>' +
            viewButtonsColumnHtml(g.apps) +
            '</td>';
        pendingBody.appendChild(tr);
    });

    const ciCompletedApps = applications.filter(function (a) {
        return a.status === 'ci_completed';
    });
    const ciCompletedGroups = groupLpsDashboardByMember(ciCompletedApps);

    if (ciCompletedBody) {
        ciCompletedBody.innerHTML = '';
        ciCompletedGroups.forEach(function (g) {
            const tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' +
                formatMemberUidCell(g.member_uid) +
                '</td><td>' +
                memberNameLinkCellHtml(g.member_name, g.member_uid) +
                '</td>' +
                '<td class="small">' +
                stackedAmountsHtml(g.apps) +
                '</td>' +
                '<td class="small">' +
                stackedDivsHtml(g.apps, function () {
                    return '<span class="badge bg-info">Awaiting decision</span>';
                }) +
                '</td>' +
                '<td class="small">' +
                stackedDivsHtml(g.apps, function (a) {
                    if (a.assigned_ci_staff) {
                        return '<span class="badge bg-primary">' + escapeHtml(a.ci_staff_name || 'CI') + '</span>';
                    }
                    return '<span class="text-muted">—</span>';
                }) +
                '</td>' +
                '<td class="small">' +
                stackedDivsHtml(g.apps, function (a) {
                    return '<span class="date-display">' + escapeHtml(formatSubmittedSlash(a.submitted_at)) + '</span>';
                }) +
                '</td>' +
                '<td class="small">' +
                stackedDivsHtml(g.apps, function (a) {
                    const doneStr = formatSubmittedSlash(a.ci_completed_at || a.ci_completedAt || '');
                    return '<span class="date-display">' + escapeHtml(doneStr || '—') + '</span>';
                }) +
                '</td>' +
                '<td>' +
                viewButtonsColumnHtml(g.apps) +
                '</td>';
            ciCompletedBody.appendChild(tr);
        });
    }

    const processedApps = applications.filter(function (a) {
        return a.status === 'approved' || a.status === 'rejected';
    });
    const processedGroups = groupLpsDashboardByMember(processedApps);

    processedBody.innerHTML = '';
    processedGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td>' +
            memberNameLinkCellHtml(g.member_name, g.member_uid) +
            '</td>' +
            '<td class="small">' +
            stackedAmountsHtml(g.apps) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, function (a) {
                if (a.status === 'approved') {
                    return '<span class="badge bg-success">Approved</span>';
                }
                return '<span class="badge bg-danger">Rejected</span>';
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, ciCellHtml) +
            '</td>' +
            '<td class="small">' +
            stackedDivsHtml(g.apps, function (a) {
                return '<span class="date-display">' + escapeHtml(formatSubmittedSlash(a.submitted_at)) + '</span>';
            }) +
            '</td>' +
            '<td>' +
            viewButtonsColumnHtml(g.apps) +
            '</td>';
        processedBody.appendChild(tr);
    });

    const pipelineStatCount = pipelineApps.length;
    const ciReviewStatCount = ciCompletedApps.length;
    const approvedCount = applications.filter(function (a) {
        return a.status === 'approved';
    }).length;
    const totalStat = document.querySelector('.stat-card.blue h3');
    if (totalStat) totalStat.textContent = applications.length;
    const pipelineStatCard = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
    if (pipelineStatCard) pipelineStatCard.textContent = pipelineStatCount;
    const ciReviewStatCard = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
    if (ciReviewStatCard) ciReviewStatCard.textContent = ciReviewStatCount;
    const approvedStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
    if (approvedStat) approvedStat.textContent = approvedCount;

    const pc = document.getElementById('pendingCount');
    if (pc) {
        pc.textContent = pipelineStatCount + ' In progress';
    }
    const cic = document.getElementById('ciCompletedCount');
    if (cic) {
        cic.textContent = ciReviewStatCount + ' For review';
    }
    const prc = document.getElementById('processedCount');
    if (prc) {
        prc.textContent = processedApps.length + ' Processed';
    }

    try {
        if (typeof searchApplications === 'function') {
            searchApplications('pending');
            searchApplications('ciCompleted');
            searchApplications('processed');
        }
        if (typeof filterProcessed === 'function') {
            filterProcessed();
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
    var completedApps = applications.filter(function (a) { return a.status === 'ci_completed'; });
    completedApps = completedApps.sort(function (appA, appB) {
        var sa = String(appA.submitted_at || '');
        var sb = String(appB.submitted_at || '');
        if (sb !== sa) {
            return sb.localeCompare(sa);
        }
        return (parseInt(String(appB.id || 0), 10) || 0) - (parseInt(String(appA.id || 0), 10) || 0);
    });
    const pendingGroups = groupLpsDashboardByMember(pendingApps);
    const completedGroups = groupLpsDashboardByMember(completedApps);

    pendingTbody.innerHTML = '';
    pendingGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        const actionsHtml = g.apps
            .map(function (app) {
                return (
                    '<div class="d-flex flex-wrap gap-1 align-items-center">' +
                    '<a href="/ci/review/' +
                    app.id +
                    '" class="btn btn-sm btn-warning">' +
                    '<i class="bi bi-eye"></i>' +
                    '<span class="btn-text">Start</span>' +
                    '</a>' +
                    '<button class="btn btn-sm btn-primary" onclick="syncManager.downloadApplication(' +
                    app.id +
                    ')" title="Download for offline">' +
                    '<i class="bi bi-download"></i>' +
                    '</button>' +
                    '</div>'
                );
            })
            .join('');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td><a href="' +
            memberHistoryHref(g.member_name, g.member_uid) +
            '">' +
            escapeHtml(g.member_name || '') +
            '</a></td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (app) {
                return escapeHtml(formatSubmittedShort(app.submitted_at));
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (app) {
                return escapeHtml(app.member_address || '');
            }) +
            '</td>' +
            '<td><div class="d-flex flex-column gap-1 align-items-start">' +
            actionsHtml +
            '</div></td>';
        pendingTbody.appendChild(tr);
    });

    completedTbody.innerHTML = '';
    completedGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        const viewsHtml = g.apps
            .map(function (app) {
                return (
                    '<a href="/ci/application/' +
                    app.id +
                    '" class="btn btn-sm btn-primary">' +
                    '<i class="bi bi-eye"></i>' +
                    '<span class="btn-text">View</span>' +
                    '</a>'
                );
            })
            .join('');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td><a href="' +
            memberHistoryHref(g.member_name, g.member_uid) +
            '">' +
            escapeHtml(g.member_name || '') +
            '</a></td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (app) {
                return escapeHtml(formatSubmittedShort(app.submitted_at));
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (app) {
                return escapeHtml(app.member_address || '');
            }) +
            '</td>' +
            '<td><div class="d-flex flex-column gap-1 align-items-start">' +
            viewsHtml +
            '</div></td>';
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
    if (cBadge) cBadge.textContent = completedApps.length + ' For review';

    try {
        if (typeof searchApplications === 'function') {
            searchApplications('pending');
            searchApplications('completed');
        }
    } catch (e) { /* ignore */ }

    try {
        if (typeof window.prefetchCiInterviewShellsForApps === 'function') {
            window.prefetchCiInterviewShellsForApps(applications);
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

    function adminStackedAmountsHtml(apps) {
        return stackedDashboardDivs(apps, function (a) {
            const lt = a.loan_type
                ? ' <span class="text-muted">' + escapeHtml(String(a.loan_type)) + '</span>'
                : '';
            return '<strong>' + formatMoneyPhp(a.loan_amount) + '</strong>' + lt;
        });
    }

    const forReviewGroups = groupLpsDashboardByMember(forReview);
    pendingTbody.innerHTML = '';
    forReviewGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        const actions = g.apps
            .map(function (a) {
                return (
                    '<a href="/admin/application/' +
                    a.id +
                    '" class="btn btn-sm btn-primary">' +
                    '<i class="bi bi-eye"></i>' +
                    '<span class="btn-text">Review</span>' +
                    '</a>'
                );
            })
            .join('');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td><a href="' +
            memberHistoryHref(g.member_name, g.member_uid) +
            '">' +
            escapeHtml(g.member_name || '') +
            '</a></td>' +
            '<td class="small">' +
            adminStackedAmountsHtml(g.apps) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, reviewStatusBadge) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.loan_staff_name || '');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.ci_staff_name || 'N/A');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(formatSubmittedShort(a.submitted_at));
            }) +
            '</td>' +
            '<td><div class="d-flex flex-column gap-1 align-items-start">' +
            actions +
            '</div></td>';
        pendingTbody.appendChild(tr);
    });

    const processedGroups = groupLpsDashboardByMember(processed);
    processedTbody.innerHTML = '';
    processedGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        const statuses = stackedDashboardDivs(g.apps, function (app) {
            let badgeClass = 'danger';
            if (app.status === 'approved') badgeClass = 'success';
            else if (app.status === 'deferred') badgeClass = 'warning';
            return (
                '<span class="badge bg-' +
                badgeClass +
                '">' +
                escapeHtml(
                    String(app.status || '')
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, function (l) { return l.toUpperCase(); })
                ) +
                '</span>'
            );
        });
        const actions = g.apps
            .map(function (a) {
                return (
                    '<a href="/admin/application/' +
                    a.id +
                    '" class="btn btn-sm btn-primary">' +
                    '<i class="bi bi-eye"></i>' +
                    '<span class="btn-text">View</span>' +
                    '</a>'
                );
            })
            .join('');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td><a href="' +
            memberHistoryHref(g.member_name, g.member_uid) +
            '">' +
            escapeHtml(g.member_name || '') +
            '</a></td>' +
            '<td class="small">' +
            adminStackedAmountsHtml(g.apps) +
            '</td>' +
            '<td class="small">' +
            statuses +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.loan_staff_name || '');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.ci_staff_name || 'N/A');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(formatSubmittedShort(a.submitted_at));
            }) +
            '</td>' +
            '<td><div class="d-flex flex-column gap-1 align-items-start">' +
            actions +
            '</div></td>';
        processedTbody.appendChild(tr);
    });

    const inProcessGroups = groupLpsDashboardByMember(inProcess);
    inProcessTbody.innerHTML = '';
    inProcessGroups.forEach(function (g) {
        const tr = document.createElement('tr');
        const statuses = stackedDashboardDivs(g.apps, function (app) {
            const badgeClass = app.status === 'submitted' ? 'secondary' : 'info';
            return (
                '<span class="badge bg-' +
                badgeClass +
                '">' +
                escapeHtml(
                    String(app.status || '')
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, function (l) { return l.toUpperCase(); })
                ) +
                '</span>'
            );
        });
        const reassignBtns = g.apps
            .map(function (app) {
                const ciArg = app.assigned_ci_staff != null ? app.assigned_ci_staff : null;
                return (
                    '<button type="button" class="btn btn-sm btn-warning" onclick="openReassignModal(' +
                    app.id +
                    ', ' +
                    JSON.stringify(String(app.member_name || '')) +
                    ', ' +
                    (ciArg == null ? 'null' : ciArg) +
                    ')">' +
                    '<i class="bi bi-arrow-repeat"></i>' +
                    '<span class="btn-text">Reassign CI</span>' +
                    '</button>'
                );
            })
            .join('');
        tr.innerHTML =
            '<td>' +
            formatMemberUidCell(g.member_uid) +
            '</td><td><a href="' +
            memberHistoryHref(g.member_name, g.member_uid) +
            '">' +
            escapeHtml(g.member_name || '') +
            '</a></td>' +
            '<td class="small">' +
            adminStackedAmountsHtml(g.apps) +
            '</td>' +
            '<td class="small">' +
            statuses +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.loan_staff_name || '');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(a.ci_staff_name || 'Not Assigned');
            }) +
            '</td>' +
            '<td class="small">' +
            stackedDashboardDivs(g.apps, function (a) {
                return escapeHtml(formatSubmittedShort(a.submitted_at));
            }) +
            '</td>' +
            '<td><div class="d-flex flex-column gap-1 align-items-start">' +
            reassignBtns +
            '</div></td>';
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

        const date = formatSubmittedShort(app.submitted_at);

        let badgeClass = 'warning';
        if (app.status === 'approved') badgeClass = 'success';
        else if (app.status === 'disapproved' || app.status === 'rejected') badgeClass = 'danger';
        else if (app.status === 'ci_completed') badgeClass = 'info';

        if (currentDashboard === 'admin') {
            row.innerHTML = `
                <td>${formatMemberUidCell(app.member_uid)}</td>
                <td><a href="${memberHistoryHref(app.member_name, app.member_uid)}">${escapeHtml(app.member_name)}</a></td>
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
                <td>${formatMemberUidCell(app.member_uid)}</td>
                <td><a href="${memberHistoryHref(app.member_name, app.member_uid)}">${escapeHtml(app.member_name)}</a></td>
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
                <td>${formatMemberUidCell(app.member_uid)}</td>
                <td><a href="${memberHistoryHref(app.member_name, app.member_uid)}">${escapeHtml(app.member_name)}</a></td>
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
