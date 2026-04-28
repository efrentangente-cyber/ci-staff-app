// Cross-tab heartbeat (localStorage) — used for optional future UX; does NOT log out on navigate.
//
// IMPORTANT: We intentionally do NOT POST /logout on pagehide/beforeunload.
// On a classic multi-page app (MPA), pagehide fires on every same-origin navigation as well as tab close.
// Heuristics (timing, click detection) caused false logouts — e.g. CI staff clicking "Start" then a slow
// server response (>5s) looked like "tab closed" and ended the session mid-workflow.
//
// Session end remains: explicit Log out, idle/session limits in app.py, and browser session cookies.

(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';
    var HEARTBEAT_MS = 8000;
    var STALE_MS = 24000;

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
}());
