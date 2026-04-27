// CI dashboard: show assigned applications from server + IndexedDB (incl. Android WebView
// and “sync failed but downloaded” cases). Merges main offline DB, mirror DB, and /api/ci_applications.
(function () {
    'use strict';

    if (!window.location.pathname.includes('/ci/dashboard')) {
        return;
    }

    var MIRROR_DB = 'CIStaffOfflineDB';
    var MIRROR_VER = 1;
    var MIRROR_STORE = 'serverApplications';
    var _hydrateScheduled = null;

    function escapeHtml(s) {
        if (s == null) {
            return '';
        }
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatSubmittedAt(v) {
        if (v == null || v === '') {
            return '—';
        }
        var s = String(v);
        if (s.length >= 10) {
            return s.substring(8, 10) + '-' + s.substring(5, 7) + '-' + s.substring(2, 4);
        }
        return s;
    }

    function appSort(a, b) {
        return (a.id || 0) - (b.id || 0);
    }

    function mergeById(first, second) {
        var map = {};
        var i;
        var a;
        var id;
        if (first && first.length) {
            for (i = 0; i < first.length; i++) {
                a = first[i];
                if (a && a.id != null) {
                    map[a.id] = a;
                }
            }
        }
        if (second && second.length) {
            for (i = 0; i < second.length; i++) {
                a = second[i];
                if (a && a.id != null) {
                    id = a.id;
                    if (map[id]) {
                        map[id] = Object.assign({}, a, map[id]);
                    } else {
                        map[id] = a;
                    }
                }
            }
        }
        return Object.keys(map)
            .map(function (k) {
                return map[k];
            })
            .sort(appSort);
    }

    function readMirrorApplications() {
        return new Promise(function (resolve) {
            if (!window.indexedDB) {
                resolve([]);
                return;
            }
            var req = indexedDB.open(MIRROR_DB, MIRROR_VER);
            req.onerror = function () {
                resolve([]);
            };
            req.onsuccess = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(MIRROR_STORE)) {
                    db.close();
                    resolve([]);
                    return;
                }
                try {
                    var tx = db.transaction([MIRROR_STORE], 'readonly');
                    var st = tx.objectStore(MIRROR_STORE);
                    var g = st.getAll();
                    g.onsuccess = function () {
                        var rows = g.result || [];
                        var apps = rows.map(function (r) {
                            return {
                                id: r.serverId,
                                member_name: r.memberName,
                                member_address: r.memberAddress,
                                status: r.status,
                                submitted_at: r.submittedAt
                            };
                        });
                        db.close();
                        resolve(apps);
                    };
                    g.onerror = function () {
                        db.close();
                        resolve([]);
                    };
                } catch (e) {
                    try {
                        db.close();
                    } catch (e2) {
                        void 0;
                    }
                    resolve([]);
                }
            };
        });
    }

    function fetchServerApplications() {
        return fetch('/api/ci_applications', {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' }
        })
            .then(function (r) {
                if (!r.ok) {
                    return null;
                }
                return r.json().catch(function () {
                    return null;
                });
            })
            .catch(function () {
                return null;
            });
    }

    function waitForDbManager(maxMs) {
        return new Promise(function (resolve) {
            var t0 = Date.now();
            function check() {
                if (window.dbManager && typeof window.dbManager.getAllApplications === 'function') {
                    resolve(true);
                    return;
                }
                if (Date.now() - t0 > maxMs) {
                    resolve(false);
                    return;
                }
                setTimeout(check, 50);
            }
            check();
        });
    }

    function renderRows(pending, completed) {
        var pendingTbody = document.querySelector('#pendingTable tbody');
        var completedTbody = document.querySelector('#completedTable tbody');
        if (!pendingTbody || !completedTbody) {
            return;
        }

        if (pending.length === 0) {
            pendingTbody.innerHTML =
                '<tr><td colspan="4" class="text-muted text-center py-3">No pending interviews. Download from the list above when online, or use the cloud download button.</td></tr>';
        } else {
            pendingTbody.innerHTML = pending
                .sort(appSort)
                .map(function (app) {
                    var id = app.id;
                    var name = escapeHtml(app.member_name || '');
                    var loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td><strong>#' +
                        id +
                        '</strong> ' +
                        name +
                        '</td>' +
                        '<td>' +
                        formatSubmittedAt(app.submitted_at) +
                        '</td>' +
                        '<td>' +
                        loc +
                        '</td>' +
                        '<td>' +
                        '<a href="/ci/review/' +
                        id +
                        '" class="btn btn-sm btn-warning"><i class="bi bi-eye"></i> <span class="btn-text">Start</span></a> ' +
                        (typeof window.syncManager !== 'undefined' && window.syncManager
                            ? '<button type="button" class="btn btn-sm btn-primary" onclick="syncManager.downloadApplication(' +
                              id +
                              ')" title="Re-download for offline"><i class="bi bi-download"></i></button>'
                            : '') +
                        '</td></tr>'
                    );
                })
                .join('');
        }

        if (completed.length === 0) {
            completedTbody.innerHTML =
                '<tr><td colspan="4" class="text-muted text-center py-3">No completed interviews in local cache yet.</td></tr>';
        } else {
            completedTbody.innerHTML = completed
                .sort(appSort)
                .map(function (app) {
                    var id = app.id;
                    var name = escapeHtml(app.member_name || '');
                    var loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td><strong>#' +
                        id +
                        '</strong> ' +
                        name +
                        '</td>' +
                        '<td>' +
                        formatSubmittedAt(app.submitted_at) +
                        '</td>' +
                        '<td>' +
                        loc +
                        '</td>' +
                        '<td><a href="/ci/review/' +
                        id +
                        '" class="btn btn-sm btn-primary"><i class="bi bi-eye"></i> <span class="btn-text">View</span></a></td></tr>'
                    );
                })
                .join('');
        }
    }

    function updateStats(all, pending, completed) {
        var n = all.length;
        var p = pending.length;
        var c = completed.length;
        var rate = n > 0 ? Math.round((c / n) * 100) : 0;

        var t = document.getElementById('ciStatTotal');
        var a = document.getElementById('ciStatPending');
        var b = document.getElementById('ciStatCompleted');
        var r = document.getElementById('ciStatRate');
        if (t) {
            t.textContent = String(n);
        }
        if (a) {
            a.textContent = String(p);
        }
        if (b) {
            b.textContent = String(c);
        }
        if (r) {
            r.textContent = String(rate) + '%';
        }

        var pendingBadge = document.getElementById('pendingCount');
        var completedBadge = document.getElementById('completedCount');
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
        var list = Array.isArray(apps) ? apps : [];
        var pending = list.filter(function (a) {
            return a && a.status === 'assigned_to_ci';
        });
        var completed = list.filter(function (a) {
            return a && a.status === 'ci_completed';
        });
        renderRows(pending, completed);
        updateStats(list, pending, completed);
    }

    function runCiDashboardHydration() {
        if (typeof window.dbManager === 'undefined' || !window.dbManager) {
            return Promise.resolve();
        }
        if (typeof window.dbManager.getAllApplications !== 'function') {
            return Promise.resolve();
        }

        return window.dbManager
            .getAllApplications()
            .catch(function () {
                return [];
            })
            .then(function (idbApps) {
                return readMirrorApplications().then(function (mirrorApps) {
                    var idb = idbApps || [];
                    var mirror = mirrorApps || [];
                    var localMerged = mergeById(idb, mirror);
                    if (typeof navigator !== 'undefined' && navigator.onLine) {
                        return fetchServerApplications().then(function (api) {
                            if (api && Array.isArray(api) && api.length > 0) {
                                return mergeById(api, localMerged);
                            }
                            if (api && Array.isArray(api) && api.length === 0) {
                                return localMerged;
                            }
                            return localMerged;
                        });
                    }
                    return localMerged;
                });
            })
            .then(function (merged) {
                if (merged && merged.length > 0) {
                    document.body.setAttribute('data-ci-offline-hydrated', '1');
                    applyFromApps(merged);
                } else {
                    if (typeof navigator !== 'undefined' && !navigator.onLine) {
                        var pt = document.querySelector('#pendingTable tbody');
                        var ct = document.querySelector('#completedTable tbody');
                        if (pt) {
                            pt.innerHTML =
                                '<tr><td colspan="4" class="text-muted text-center py-3">No applications in offline storage. Connect to the internet and use Download on each row, or the cloud download button.</td></tr>';
                        }
                        if (ct) {
                            ct.innerHTML =
                                '<tr><td colspan="4" class="text-muted text-center py-3">—</td></tr>';
                        }
                        updateStats([], [], []);
                    }
                }
            });
    }

    function scheduleHydration() {
        if (_hydrateScheduled) {
            clearTimeout(_hydrateScheduled);
        }
        _hydrateScheduled = setTimeout(function () {
            _hydrateScheduled = null;
            waitForDbManager(6000).then(function () {
                return runCiDashboardHydration();
            });
        }, 0);
    }

    function onOfflineDataUpdated(ev) {
        var apps = ev.detail && ev.detail.applications;
        if (apps && apps.length) {
            applyFromApps(apps);
        } else {
            scheduleHydration();
        }
    }

    window.addEventListener('offline-data-updated', onOfflineDataUpdated);
    window.addEventListener('offline', scheduleHydration);
    window.addEventListener('online', scheduleHydration);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            scheduleHydration();
            setTimeout(scheduleHydration, 400);
            setTimeout(scheduleHydration, 2000);
        });
    } else {
        scheduleHydration();
        setTimeout(scheduleHydration, 400);
        setTimeout(scheduleHydration, 2000);
    }
})();
