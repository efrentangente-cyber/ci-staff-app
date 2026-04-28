// Cross-tab heartbeat + optional logout when this browser TAB is closed (X), not when navigating inside the app.
//
// MPAs fire pagehide on EVERY full-page navigation AND on tab close — indistinguishable by itself.
// We skip logout when we detect same-origin navigation intent (links, forms, keyboard Back shortcut).
// We only POST /logout when pagehide fires AND no intent AND no other live tab remains (localStorage map).

(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';
    var NAV_INTENT_KEY = 'dccco_nav_intent_ts';

    try {
        sessionStorage.removeItem(NAV_INTENT_KEY);
    } catch (e) { /* */ }

    var HEARTBEAT_MS = 8000;
    var STALE_MS = 24000;
    /** Cover slow servers / laggy devices — navigation intent suppresses tab-close logout */
    var NAV_INTENT_MS = 180000;

    function csrfToken() {
        try {
            var m = document.querySelector('meta[name="csrf-token"]');
            return m ? m.getAttribute('content') : '';
        } catch (e) {
            return '';
        }
    }

    function markNavigationIntent() {
        try {
            sessionStorage.setItem(NAV_INTENT_KEY, String(Date.now()));
        } catch (e) { /* private mode */ }
    }

    // Programmatic form.submit() does NOT fire "submit" events — CI checklist wizard uses it.
    // Without this, pagehide thinks the tab closed and POSTs /logout during the same navigation.
    try {
        var nativeFormSubmit = HTMLFormElement.prototype.submit;
        HTMLFormElement.prototype.submit = function () {
            markNavigationIntent();
            return nativeFormSubmit.apply(this, arguments);
        };
    } catch (eSubmit) { /* */ }

    function recentNavigationIntent() {
        try {
            var raw = sessionStorage.getItem(NAV_INTENT_KEY);
            if (!raw) return false;
            var ts = parseInt(raw, 10);
            if (isNaN(ts)) return false;
            return Date.now() - ts < NAV_INTENT_MS;
        } catch (e2) {
            return false;
        }
    }

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

    function sameOriginHref(el) {
        if (!el || !el.href) return false;
        try {
            var u = new URL(el.href, window.location.href);
            return u.origin === window.location.origin;
        } catch (e) {
            return false;
        }
    }

    function maybeMarkAnchorIntent(ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var a = t.closest('a[href]');
        if (!a) return;
        var href = a.getAttribute('href');
        if (!href || href.charAt(0) === '#' ||
            href.indexOf('javascript:') === 0 ||
            href.indexOf('mailto:') === 0 ||
            href.indexOf('tel:') === 0) {
            return;
        }
        if (!sameOriginHref(a)) return;
        markNavigationIntent();
    }

    document.addEventListener('mousedown', maybeMarkAnchorIntent, true);
    document.addEventListener('touchstart', maybeMarkAnchorIntent, true);
    document.addEventListener('click', maybeMarkAnchorIntent, true);

    document.addEventListener('submit', function () {
        markNavigationIntent();
    }, true);

    document.addEventListener('keydown', function (ev) {
        try {
            if (ev.altKey && (ev.key === 'ArrowLeft' || ev.keyCode === 37)) {
                markNavigationIntent();
            }
            if (ev.metaKey && (ev.key === '[' || ev.keyCode === 219)) {
                markNavigationIntent();
            }
        } catch (e) { /* */ }
    }, true);

    heartbeat();
    setInterval(heartbeat, HEARTBEAT_MS);

    window.addEventListener('pagehide', function (event) {
        if (event.persisted) return;

        try {
            if (!document.body.classList.contains('authenticated')) return;

            if (recentNavigationIntent()) return;

            var map = purgeStale(readMap());
            var id = tabId();
            delete map[id];
            writeMap(map);

            if (Object.keys(map).length > 0) return;

            var tok = csrfToken();
            if (!tok) return;

            fetch('/logout', {
                method: 'POST',
                credentials: 'same-origin',
                keepalive: true,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': tok,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: 'csrf_token=' + encodeURIComponent(tok)
            }).catch(function () {});
        } catch (e2) { /* */ }
    });
}());
