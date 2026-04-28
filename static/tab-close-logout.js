// Cross-tab heartbeat (localStorage) — tracks concurrent app tabs for diagnostics/UI only.
//
// We do NOT POST /logout from pagehide: browsers fire pagehide for normal navigation AND for closing a
// tab, so automatic logout looked like "I get signed out whenever I navigate". Session security uses
// server-side idle expiry, enforce_single_active_login, and explicit Log out.

(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';

    var HEARTBEAT_MS = 12000;
    var STALE_MS = 36000;

    function tabId() {
        try {
            var id = sessionStorage.getItem('dccco_tab_id');
            if (!id) {
                id = (typeof crypto !== 'undefined' && crypto.randomUUID)
                    ? crypto.randomUUID()
                    : ('t' + Date.now() + '_' + Math.random().toString(36).slice(2));
                sessionStorage.setItem('dccco_tab_id', id);
            }
            return id;
        } catch (e) {
            return 'fallback_' + Date.now();
        }
    }

    function readMap() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }

    function writeMap(obj) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
        } catch (e) { /* quota / private mode */ }
    }

    function purgeStale(map) {
        var now = Date.now();
        var out = {};
        Object.keys(map).forEach(function (k) {
            if (now - map[k] < STALE_MS) {
                out[k] = map[k];
            }
        });
        return out;
    }

    function heartbeat() {
        var id = tabId();
        var map = purgeStale(readMap());
        map[id] = Date.now();
        writeMap(map);
    }

    heartbeat();
    setInterval(heartbeat, HEARTBEAT_MS);

    window.addEventListener('pagehide', function (event) {
        if (event.persisted) return;

        try {
            if (!document.body.classList.contains('authenticated')) return;

            var map = purgeStale(readMap());
            var id = tabId();
            delete map[id];
            writeMap(map);
        } catch (e2) { /* */ }
    });
}());
