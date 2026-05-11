// Cross-tab heartbeat (localStorage) + logout when the last authenticated tab/window closes.
//
// We skip logout when the unload is likely an in-app navigation (same-origin link click,
// form submit, or reload shortcut) using a short-lived sessionStorage flag, because
// pagehide alone cannot distinguish "tab closed" from "navigate to another page".

(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';
    var EXPECT_NAV_KEY = 'dccco_expect_nav';

    var HEARTBEAT_MS = 12000;
    // Drop entries older than this so "dead" tabs don't block last-tab logout forever.
    // Keep generous — throttled background tabs may miss heartbeats for tens of seconds.
    var STALE_MS = 120000;

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

    function setExpectInAppNavigation() {
        try {
            sessionStorage.setItem(EXPECT_NAV_KEY, '1');
        } catch (e) { /* */ }
    }

    function consumeExpectInAppNavigation() {
        try {
            if (sessionStorage.getItem(EXPECT_NAV_KEY) === '1') {
                sessionStorage.removeItem(EXPECT_NAV_KEY);
                return true;
            }
        } catch (e) { /* */ }
        return false;
    }

    /* In-app navigation: same-origin <a> / <form> (not new tab, not download). */
    document.addEventListener('click', function (e) {
        var t = e.target && e.target.closest ? e.target.closest('a[href]') : null;
        if (!t) {
            return;
        }
        if (t.hasAttribute('download')) {
            return;
        }
        var tgt = (t.getAttribute('target') || '').toLowerCase().trim();
        if (tgt === '_blank') {
            return;
        }
        var href = t.getAttribute('href');
        if (!href || href[0] === '#' || href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) {
            return;
        }
        var u;
        try {
            u = new URL(t.href, location.href);
        } catch (x) {
            return;
        }
        if (u.origin !== location.origin) {
            return;
        }
        setExpectInAppNavigation();
    }, true);

    document.addEventListener('submit', function () {
        setExpectInAppNavigation();
    }, true);

    /* Browser reload / hard refresh — would otherwise look like "tab gone". */
    window.addEventListener('keydown', function (e) {
        var isReload = e.key === 'F5' ||
            (e.ctrlKey && (e.key === 'r' || e.key === 'R')) ||
            (e.metaKey && (e.key === 'r' || e.key === 'R'));
        if (isReload) {
            setExpectInAppNavigation();
        }
    }, true);

    /**
     * JS redirects (location.href / assign / replace / reload) do not fire link-click handlers.
     * Without this, pagehide looks like "tab closed" and the last tab would GET /logout mid-workflow.
     */
    function patchLocationNavHooks() {
        try {
            var L = window.location;
            var assignOrig = L.assign.bind(L);
            L.assign = function (url) {
                try {
                    var x = new URL(String(url), location.href);
                    if (x.origin === location.origin) {
                        setExpectInAppNavigation();
                    }
                } catch (e) { /* */ }
                return assignOrig(url);
            };
            var replaceOrig = L.replace.bind(L);
            L.replace = function (url) {
                try {
                    var x = new URL(String(url), location.href);
                    if (x.origin === location.origin) {
                        setExpectInAppNavigation();
                    }
                } catch (e) { /* */ }
                return replaceOrig(url);
            };
            var reloadOrig = L.reload.bind(L);
            L.reload = function () {
                setExpectInAppNavigation();
                return reloadOrig();
            };
            var desc = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
            if (desc && desc.set) {
                Object.defineProperty(L, 'href', {
                    set: function (v) {
                        try {
                            var x = new URL(String(v), location.href);
                            if (x.origin === location.origin) {
                                setExpectInAppNavigation();
                            }
                        } catch (e) { /* */ }
                        desc.set.call(L, v);
                    },
                    get: desc.get,
                    configurable: true,
                    enumerable: true,
                });
            }
        } catch (e) { /* strict mode / exotic browsers */ }
    }

    patchLocationNavHooks();

    heartbeat();
    setInterval(heartbeat, HEARTBEAT_MS);

    function endSessionIfLastTab() {
        try {
            fetch(new URL('/logout', location.origin).href, {
                method: 'GET',
                credentials: 'same-origin',
                keepalive: true,
                cache: 'no-store',
            }).catch(function () {});
        } catch (e2) { /* */ }
    }

    window.addEventListener('pagehide', function (event) {
        if (event.persisted) {
            return;
        }

        try {
            if (!document.body.classList.contains('authenticated')) {
                return;
            }

            var internalNav = consumeExpectInAppNavigation();

            var map = purgeStale(readMap());
            var id = tabId();
            delete map[id];
            writeMap(map);

            /* In-app navigation: map may be empty until the next page heartbeats; never logout. */
            if (internalNav) {
                return;
            }

            if (Object.keys(map).length === 0) {
                endSessionIfLastTab();
            }
        } catch (e3) { /* */ }
    });
}());
