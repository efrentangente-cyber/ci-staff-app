// CI dashboard: show assigned applications from server + IndexedDB (incl. Android WebView
// and “sync failed but downloaded” cases). Merges main offline DB, mirror DB, and /api/ci_applications.
(function () {
    'use strict';

    if (!window.location.pathname.includes('/ci/dashboard')) {
        return;
    }

    var MIRROR_DB = 'CIStaffOfflineDB';
    /** Bumped when schema repair is needed; onupgradeneeded ensures serverApplications exists. */
    var MIRROR_VER = 3;
    var MIRROR_STORE = 'serverApplications';
    var _hydrateScheduled = null;

    /** Chromium often throws with message "...object stores was not found" without name === NotFoundError. */
    function isMissingMirrorStoreError(err) {
        if (!err) {
            return false;
        }
        if (err.name === 'NotFoundError' || err.name === 'InvalidAccessError') {
            return true;
        }
        var msg = String(err.message || '');
        if (msg.indexOf('mirror_store_missing') !== -1) {
            return true;
        }
        if (msg.indexOf('object stores was not found') !== -1) {
            return true;
        }
        if (msg.indexOf('object store was not found') !== -1) {
            return true;
        }
        return false;
    }

    function deleteMirrorDatabase() {
        return new Promise(function (resolve, reject) {
            var del = indexedDB.deleteDatabase(MIRROR_DB);
            del.onerror = function () {
                reject(del.error || new Error('deleteDatabase'));
            };
            del.onsuccess = function () {
                resolve();
            };
            del.onblocked = function () {
                setTimeout(function () {
                    var del2 = indexedDB.deleteDatabase(MIRROR_DB);
                    del2.onerror = function () {
                        reject(del2.error || new Error('deleteDatabase blocked'));
                    };
                    del2.onsuccess = function () {
                        resolve();
                    };
                }, 400);
            };
        });
    }

    /**
     * Single IndexedDB open for read + write paths.
     * Previously readMirrorApplications used open() with no onupgradeneeded — first visit could create
     * version 1 with zero object stores; later saves then threw "object store not found".
     */
    function openMirrorDatabase() {
        return new Promise(function (resolve, reject) {
            if (!window.indexedDB) {
                reject(new Error('IndexedDB unavailable'));
                return;
            }
            var req = indexedDB.open(MIRROR_DB, MIRROR_VER);
            req.onerror = function () {
                reject(req.error);
            };
            req.onblocked = function () {
                reject(new Error('IndexedDB upgrade blocked (close other tabs using this site)'));
            };
            req.onupgradeneeded = function (ev) {
                var db = ev.target.result;
                if (!db.objectStoreNames.contains(MIRROR_STORE)) {
                    db.createObjectStore(MIRROR_STORE, { keyPath: 'serverId' });
                }
            };
            req.onsuccess = function () {
                var db = req.result;
                if (!db.objectStoreNames.contains(MIRROR_STORE)) {
                    try {
                        db.close();
                    } catch (eClose) {
                        void 0;
                    }
                    reject(new Error('mirror_store_missing'));
                    return;
                }
                resolve(db);
            };
        });
    }

    function openMirrorDbWritable() {
        return openMirrorDatabase();
    }

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
        if (v instanceof Date) {
            v = v.toISOString();
        }
        var str = String(v).trim();
        var d = new Date(str);
        if (!Number.isNaN(d.getTime())) {
            var dd = String(d.getDate()).padStart(2, '0');
            var mm = String(d.getMonth() + 1).padStart(2, '0');
            var yy = String(d.getFullYear()).slice(-2);
            return dd + '-' + mm + '-' + yy;
        }
        if (str.length >= 10 && str[4] === '-' && str[7] === '-') {
            return str.slice(8, 10) + '-' + str.slice(5, 7) + '-' + str.slice(2, 4);
        }
        return str;
    }

    function appSort(a, b) {
        return (a.id || 0) - (b.id || 0);
    }

    /** Newest submission first — matches CI dashboard Completed table server sort. */
    function appSortCompletedNewestFirst(a, b) {
        var sa = String(a.submitted_at || '');
        var sb = String(b.submitted_at || '');
        if (sb !== sa) {
            return sb.localeCompare(sa);
        }
        return (b.id || 0) - (a.id || 0);
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

    function dictToMirrorRow(app) {
        if (!app || app.id == null) {
            return null;
        }
        var snap = app;
        try {
            snap = JSON.parse(JSON.stringify(app));
        } catch (eSnap) {
            snap = app;
        }
        var mu = app.member_uid;
        if (mu == null && snap && snap.member_uid != null) {
            mu = snap.member_uid;
        }
        return {
            serverId: app.id,
            memberName: app.member_name || '',
            memberAddress: app.member_address || '',
            status: app.status || '',
            submittedAt: app.submitted_at || '',
            memberUid: mu,
            fullRecord: snap
        };
    }

    function saveMirrorApplicationsFromDicts(appDicts) {
        var rows = [];
        if (appDicts && appDicts.length) {
            var i;
            for (i = 0; i < appDicts.length; i++) {
                var r = dictToMirrorRow(appDicts[i]);
                if (r) {
                    rows.push(r);
                }
            }
        }
        if (!rows.length) {
            return Promise.resolve(0);
        }
        function doPut(db) {
            return new Promise(function (resolve, reject) {
                try {
                    var tx = db.transaction([MIRROR_STORE], 'readwrite');
                    var st = tx.objectStore(MIRROR_STORE);
                    var j;
                    for (j = 0; j < rows.length; j++) {
                        st.put(rows[j]);
                    }
                    tx.oncomplete = function () {
                        try {
                            db.close();
                        } catch (eClose) {
                            void 0;
                        }
                        resolve(rows.length);
                    };
                    tx.onerror = function () {
                        try {
                            db.close();
                        } catch (eClose2) {
                            void 0;
                        }
                        reject(tx.error);
                    };
                } catch (e) {
                    try {
                        db.close();
                    } catch (eClose3) {
                        void 0;
                    }
                    reject(e);
                }
            });
        }
        function runPut() {
            return openMirrorDatabase().then(function (db) {
                return doPut(db);
            });
        }

        return runPut().catch(function (err) {
            if (!isMissingMirrorStoreError(err)) {
                return Promise.reject(err);
            }
            return deleteMirrorDatabase().then(function () {
                return runPut();
            });
        });
    }

    /**
     * Fetch JSON APIs without following redirects into HTML login pages (was confusing / looked like random logout).
     */
    function fetchCiApiJson(url) {
        return fetch(url, {
            credentials: 'same-origin',
            redirect: 'manual',
            headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (r) {
            if (r.type === 'opaqueredirect') {
                window.location.href = '/login';
                return null;
            }
            if (r.status >= 300 && r.status < 400) {
                window.location.href = '/login';
                return null;
            }
            if (r.status === 401 || r.status === 403) {
                window.location.href = '/login';
                return null;
            }
            if (!r.ok) {
                return Promise.reject(new Error('HTTP ' + r.status));
            }
            return r.json();
        });
    }

    function readMirrorApplications() {
        if (!window.indexedDB) {
            return Promise.resolve([]);
        }
        return openMirrorDatabase()
            .then(function (db) {
                return new Promise(function (resolve) {
                    try {
                        var tx = db.transaction([MIRROR_STORE], 'readonly');
                        var st = tx.objectStore(MIRROR_STORE);
                        var g = st.getAll();
                        g.onsuccess = function () {
                            var rows = g.result || [];
                            var apps = rows.map(function (r) {
                                if (r.fullRecord && typeof r.fullRecord === 'object') {
                                    var o = Object.assign({}, r.fullRecord);
                                    if (o.id == null && r.serverId != null) {
                                        o.id = r.serverId;
                                    }
                                    return o;
                                }
                                return {
                                    id: r.serverId,
                                    member_name: r.memberName,
                                    member_address: r.memberAddress,
                                    status: r.status,
                                    submitted_at: r.submittedAt,
                                    member_uid: r.memberUid != null ? r.memberUid : undefined
                                };
                            });
                            try {
                                db.close();
                            } catch (eClose) {
                                void 0;
                            }
                            resolve(apps);
                        };
                        g.onerror = function () {
                            try {
                                db.close();
                            } catch (eClose2) {
                                void 0;
                            }
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
                });
            })
            .catch(function () {
                return [];
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

    function memberHistoryHrefOffline(memberName, memberUid) {
        var base = typeof window.__MEMBER_HISTORY_URL === 'string' ? window.__MEMBER_HISTORY_URL : '/loan/member';
        var mu = memberUid != null && memberUid !== '' ? String(memberUid).trim() : '';
        var next =
            typeof window.location !== 'undefined' && window.location.pathname
                ? '&next=' + encodeURIComponent(window.location.pathname + window.location.search)
                : '';
        if (mu !== '' && /^\d+$/.test(mu)) {
            return base + '?member_uid=' + encodeURIComponent(mu) + next;
        }
        return base + '?name=' + encodeURIComponent(memberName || '') + next;
    }

    function renderRows(pending, completed) {
        var pendingTbody = document.querySelector('#pendingTable tbody');
        var completedTbody = document.querySelector('#completedTable tbody');
        if (!pendingTbody || !completedTbody) {
            return;
        }

        if (pending.length === 0) {
            pendingTbody.innerHTML =
                '<tr><td colspan="5" class="text-muted text-center py-3">No pending interviews. When online, assignments appear here and are kept on this device for offline use.</td></tr>';
        } else {
            pendingTbody.innerHTML = pending
                .sort(appSort)
                .map(function (app) {
                    var id = app.id;
                    var mu =
                        app.member_uid != null && app.member_uid !== ''
                            ? escapeHtml(String(app.member_uid))
                            : '<span class="text-muted">—</span>';
                    var nameRaw = app.member_name || '';
                    var nameEsc = escapeHtml(nameRaw);
                    var nameHref = memberHistoryHrefOffline(nameRaw, app.member_uid);
                    var loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td class="text-nowrap">' +
                        mu +
                        '</td>' +
                        '<td><a href="' +
                        nameHref +
                        '">' +
                        nameEsc +
                        '</a></td>' +
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
                '<tr><td colspan="5" class="text-muted text-center py-3">No completed interviews in local cache yet.</td></tr>';
        } else {
            completedTbody.innerHTML = completed
                .sort(appSortCompletedNewestFirst)
                .map(function (app) {
                    var id = app.id;
                    var mu =
                        app.member_uid != null && app.member_uid !== ''
                            ? escapeHtml(String(app.member_uid))
                            : '<span class="text-muted">—</span>';
                    var nameRaw = app.member_name || '';
                    var nameEsc = escapeHtml(nameRaw);
                    var nameHref = memberHistoryHrefOffline(nameRaw, app.member_uid);
                    var loc = escapeHtml(app.member_address || '—');
                    return (
                        '<tr>' +
                        '<td class="text-nowrap">' +
                        mu +
                        '</td>' +
                        '<td><a href="' +
                        nameHref +
                        '">' +
                        nameEsc +
                        '</a></td>' +
                        '<td>' +
                        formatSubmittedAt(app.submitted_at) +
                        '</td>' +
                        '<td>' +
                        loc +
                        '</td>' +
                        '<td><a href="/ci/application/' +
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
        var idbPromise =
            window.dbManager && typeof window.dbManager.getAllApplications === 'function'
                ? window.dbManager.getAllApplications().catch(function () {
                      return [];
                  })
                : Promise.resolve([]);

        return idbPromise
            .then(function (idbApps) {
                return readMirrorApplications().then(function (mirrorApps) {
                    var idb = idbApps || [];
                    var mirror = mirrorApps || [];
                    var localMerged = mergeById(idb, mirror);
                    if (typeof navigator !== 'undefined' && navigator.onLine) {
                        return fetchServerApplications().then(function (api) {
                            if (api && Array.isArray(api) && api.length > 0) {
                                saveMirrorApplicationsFromDicts(api).catch(function () {});
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
                                '<tr><td colspan="5" class="text-muted text-center py-3">No assignments saved on this device yet. Connect once with internet — your dashboard saves automatically — or use the cloud download button.</td></tr>';
                        }
                        if (ct) {
                            ct.innerHTML =
                                '<tr><td colspan="5" class="text-muted text-center py-3">—</td></tr>';
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
            waitForDbManager(400).then(function () {
                return runCiDashboardHydration();
            });
        }, 0);
    }

    window.syncManager = {
        downloadApplication: function (appId) {
            var id = parseInt(appId, 10);
            if (!id) {
                return;
            }
            fetchCiApiJson('/api/ci_application/' + id)
                .then(function (data) {
                    if (!data || !data.application) {
                        return null;
                    }
                    return saveMirrorApplicationsFromDicts([data.application]).then(function () {
                        return data.application;
                    });
                })
                .then(function (app) {
                    if (!app) {
                        return;
                    }
                    alert('Application #' + id + ' saved for offline review.');
                    window.dispatchEvent(
                        new CustomEvent('offline-data-updated', {
                            detail: { applications: [app] }
                        })
                    );
                    scheduleHydration();
                })
                .catch(function (err) {
                    alert('Download failed: ' + (err && err.message ? err.message : err));
                });
        },
        downloadAllPending: function () {
            fetchCiApiJson('/api/ci/download_applications')
                .then(function (data) {
                    if (!data || !data.success || !data.applications) {
                        alert('Nothing to download or the server returned an error.');
                        return null;
                    }
                    var apps = data.applications;
                    if (!apps.length) {
                        alert('No pending applications to cache offline.');
                        return null;
                    }
                    return saveMirrorApplicationsFromDicts(apps).then(function () {
                        return apps;
                    });
                })
                .then(function (apps) {
                    if (!apps || !apps.length) {
                        return;
                    }
                    alert('Saved ' + apps.length + ' pending application(s) for offline use.');
                    window.dispatchEvent(
                        new CustomEvent('offline-data-updated', { detail: { applications: apps } })
                    );
                    scheduleHydration();
                })
                .catch(function (err) {
                    alert('Download failed: ' + (err && err.message ? err.message : err));
                });
        }
    };

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
