// When the last open tab/window for this app closes (or navigates away without another tab),
// POST /logout with keepalive so the server session ends — others can sign in after Log out per policy.
// Same-origin clicks/forms within a short window skip logout (full page navigations).
// Back/forward and reload skips avoid accidental logouts during normal browsing.
(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';
    var HEARTBEAT_MS = 8000;
    var STALE_MS = 24000;
    var SAME_SITE_NAV_MS = 5000;

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

    function countOtherLiveTabs() {
        var id = tabId();
        var map = purgeStale(readMap());
        var now = Date.now();
        var n = 0;
        Object.keys(map).forEach(function (k) {
            if (k !== id && (now - map[k] < STALE_MS)) {
                n++;
            }
        });
        return n;
    }

    function markSameSiteNavigationIntent() {
        try {
            sessionStorage.setItem('dccco_nav_click_ts', String(Date.now()));
        } catch (e) { /* ignore */ }
    }

    document.addEventListener('click', function (ev) {
        var a = ev.target && ev.target.closest && ev.target.closest('a[href]');
        if (!a || a.target === '_blank' || a.download) {
            return;
        }
        var href = a.getAttribute('href');
        if (!href || href.charAt(0) === '#' || href.slice(0, 11).toLowerCase() === 'javascript:') {
            return;
        }
        try {
            var u = new URL(href, window.location.href);
            if (u.origin === window.location.origin) {
                markSameSiteNavigationIntent();
            }
        } catch (e) { /* ignore */ }
    }, true);

    document.addEventListener('submit', function (ev) {
        var form = ev.target;
        if (!form || form.tagName !== 'FORM') {
            return;
        }
        try {
            var u = new URL(form.action || window.location.pathname, window.location.href);
            if (u.origin === window.location.origin) {
                markSameSiteNavigationIntent();
            }
        } catch (e2) { /* ignore */ }
    }, true);

    function recentSameSiteClick() {
        try {
            var ts = parseInt(sessionStorage.getItem('dccco_nav_click_ts') || '0', 10);
            if (!ts) {
                return false;
            }
            return (Date.now() - ts) < SAME_SITE_NAV_MS;
        } catch (e) {
            return false;
        }
    }

    function isReloadUnload() {
        try {
            if (performance.navigation && performance.navigation.type === 1) {
                return true;
            }
        } catch (e) { /* ignore */ }
        try {
            var nav = performance.getEntriesByType('navigation')[0];
            if (nav && nav.type === 'reload') {
                return true;
            }
        } catch (e2) { /* ignore */ }
        return false;
    }

    function isBackForwardUnload() {
        try {
            if (performance.navigation && performance.navigation.type === 2) {
                return true;
            }
        } catch (e) { /* ignore */ }
        try {
            var nav = performance.getEntriesByType('navigation')[0];
            if (nav && nav.type === 'back_forward') {
                return true;
            }
        } catch (e2) { /* ignore */ }
        return false;
    }

    function postLogoutBeacon() {
        var csrf = document.querySelector('meta[name="csrf-token"]');
        var token = csrf && csrf.getAttribute('content');
        if (!token) {
            return;
        }
        var body = 'csrf_token=' + encodeURIComponent(token);
        var url = window.location.origin + '/logout';
        try {
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': token,
                },
                body: body,
                credentials: 'include',
                keepalive: true,
            }).catch(function () { /* ignore */ });
        } catch (err) { /* ignore */ }
    }

    heartbeat();
    setInterval(heartbeat, HEARTBEAT_MS);

    window.addEventListener('pagehide', function (ev) {
        if (!document.body.classList.contains('authenticated')) {
            return;
        }
        if (ev.persisted) {
            return;
        }
        if (isReloadUnload()) {
            return;
        }
        if (isBackForwardUnload()) {
            return;
        }
        if (recentSameSiteClick()) {
            return;
        }
        if (countOtherLiveTabs() > 0) {
            return;
        }
        postLogoutBeacon();
    }, false);
}());
