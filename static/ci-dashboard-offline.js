// Hydrate CI dashboard tables from IndexedDB so offline mode shows downloaded applications.
(function () {
    'use strict';

    if (!window.location.pathname.includes('/ci/dashboard')) {
        return;
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatSubmittedAt(v) {
        if (v == null || v === '') return '—';
        const s = String(v);
        if (s.length >= 10) {
            return s.substring(8, 10) + '-' + s.substring(5, 7) + '-' + s.substring(2, 4);
        }
        return s;
    }

    function appSort(a, b) {
        return (a.id || 0) - (b.id || 0);
    }

    function renderRows(pending, completed) {
        const pendingTbody = document.querySelector('#pendingTable tbody');
        const completedTbody = document.querySelector('#completedTable tbody');
        if (!pendingTbody || !completedTbody) {
            return;
        }

        if (pending.length === 0) {
            pendingTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-3">No pending interviews in offline cache.</td></tr>';
        } else {
            pendingTbody.innerHTML = pending
                .sort(appSort)
                .map(function (app) {
                    const id = app.id;
                    const name = escapeHtml(app.member_name || '');
                    const loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td><strong>#' + id + '</strong> ' + name + '</td>' +
                        '<td>' + formatSubmittedAt(app.submitted_at) + '</td>' +
                        '<td>' + loc + '</td>' +
                        '<td>' +
                        '<a href="/ci/review/' +
                        id +
                        '" class="btn btn-sm btn-warning">' +
                        '<i class="bi bi-eye"></i> <span class="btn-text">Start</span></a> ' +
                        '<button type="button" class="btn btn-sm btn-primary" onclick="syncManager.downloadApplication(' +
                        id +
                        ')" title="Re-download for offline"><i class="bi bi-download"></i></button>' +
                        '</td></tr>'
                    );
                })
                .join('');
        }

        if (completed.length === 0) {
            completedTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-3">No completed interviews in offline cache.</td></tr>';
        } else {
            completedTbody.innerHTML = completed
                .sort(appSort)
                .map(function (app) {
                    const id = app.id;
                    const name = escapeHtml(app.member_name || '');
                    const loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td><strong>#' + id + '</strong> ' + name + '</td>' +
                        '<td>' + formatSubmittedAt(app.submitted_at) + '</td>' +
                        '<td>' + loc + '</td>' +
                        '<td><a href="/ci/review/' +
                        id +
                        '" class="btn btn-sm btn-primary"><i class="bi bi-eye"></i> <span class="btn-text">View</span></a></td>' +
                        '</tr>'
                    );
                })
                .join('');
        }
    }

    function updateStats(all, pending, completed) {
        const n = all.length;
        const p = pending.length;
        const c = completed.length;
        const rate = n > 0 ? Math.round((c / n) * 100) : 0;

        const t = document.getElementById('ciStatTotal');
        const a = document.getElementById('ciStatPending');
        const b = document.getElementById('ciStatCompleted');
        const r = document.getElementById('ciStatRate');
        if (t) t.textContent = String(n);
        if (a) a.textContent = String(p);
        if (b) b.textContent = String(c);
        if (r) r.textContent = String(rate) + '%';

        const pendingBadge = document.getElementById('pendingCount');
        const completedBadge = document.getElementById('completedCount');
        if (pendingBadge) {
            pendingBadge.textContent = p + ' Pending';
        }
        if (completedBadge) {
            completedBadge.textContent = c + ' Completed';
        }
    }

    function applyFromApps(apps) {
        if (!apps || !apps.length) {
            return;
        }
        const list = Array.isArray(apps) ? apps : [];
        const pending = list.filter(function (a) {
            return a && a.status === 'assigned_to_ci';
        });
        const completed = list.filter(function (a) {
            return a && a.status === 'ci_completed';
        });
        renderRows(pending, completed);
        updateStats(list, pending, completed);
    }

    function tryHydrate(reason) {
        if (typeof window.dbManager === 'undefined' || !window.dbManager) {
            return;
        }
        if (typeof window.dbManager.getAllApplications !== 'function') {
            return;
        }
        window.dbManager.getAllApplications().then(function (apps) {
            apps = apps || [];
            if (reason === 'download' && apps.length === 0) {
                return;
            }
            if (!navigator.onLine) {
                if (apps.length === 0) {
                    const pt = document.querySelector('#pendingTable tbody');
                    const ct = document.querySelector('#completedTable tbody');
                    if (pt) {
                        pt.innerHTML =
                            '<tr><td colspan="4" class="text-muted text-center py-3">No applications downloaded. Connect to the internet and use the download or cloud button, or wait for auto-download.</td></tr>';
                    }
                    if (ct) {
                        ct.innerHTML =
                            '<tr><td colspan="4" class="text-muted text-center py-3">—</td></tr>';
                    }
                    updateStats([], [], []);
                    return;
                }
                document.body.setAttribute('data-ci-offline-hydrated', '1');
            }
            if (apps.length > 0) {
                applyFromApps(apps);
            }
        });
    }

    function onOfflineDataUpdated(ev) {
        const apps = ev.detail && ev.detail.applications;
        if (apps && apps.length) {
            applyFromApps(apps);
        } else {
            tryHydrate('download');
        }
    }

    window.addEventListener('offline-data-updated', onOfflineDataUpdated);

    window.addEventListener('offline', function () {
        tryHydrate('offline');
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            if (!navigator.onLine) {
                tryHydrate('offline');
            }
        });
    } else {
        if (!navigator.onLine) {
            tryHydrate('offline');
        }
    }
})();
