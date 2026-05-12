// Cross-tab registry + GET /logout when the last authenticated app tab actually closes.
// Runs only when body data-tab-close-auto-logout is true / TAB_CLOSE_AUTO_LOGOUT (opt-in; default off in app).
// Does not end the session on idle — only when the final tab is closed (and in-app navigations are excluded).
//
// We skip logout when the unload is likely an in-app navigation (same-origin link follow,
// form submit, reload shortcut, or programmatic same-origin redirect) using a short
// sessionStorage timestamp, because pagehide alone cannot distinguish "tab closed" from
// "navigate to another page".
//
// A simple consume-on-read flag is fragile on touch devices and multi-handler ordering;
// we keep a time window (EXPECT_NAV_MAX_MS) and clear the marker on pageshow.

(function () {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    var auto = (document.body.getAttribute('data-tab-close-auto-logout') || '').toLowerCase();
    if (auto !== 'true' && auto !== '1') {
        return;
    }

    var STORAGE_KEY = 'dccco_live_tabs_v1';
    var EXPECT_NAV_KEY = 'dccco_expect_nav';
    // Users often open the account menu, resume work, then click Change password minutes later.
    // 12s caused GET /logout on normal in-app navigation (single tab). An hour is safe for shared PCs.
    var EXPECT_NAV_MAX_MS = 3600000;

    var HEARTBEAT_MS = 12000;
    // Drop entries older than this so crashed tabs don't block last-tab logout forever.
    // Background tabs can be throttled heavily (mobile, long interviews) — keep very high so another
    // live tab is not "forgotten", which would make the only active tab look like "last closed".
    var STALE_MS = 21600000; // 6 hours

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
            sessionStorage.setItem(EXPECT_NAV_KEY, String(Date.now()));
        } catch (e) { /* */ }
    }

    function isRecentInAppNavigation() {
        try {
            var raw = sessionStorage.getItem(EXPECT_NAV_KEY);
            if (!raw) {
                return false;
            }
            /* Legacy single-use flag from older builds — honor once then drop. */
            if (raw === '1') {
                try {
                    sessionStorage.removeItem(EXPECT_NAV_KEY);
                } catch (e) { /* */ }
                return true;
            }
            var t = parseInt(raw, 10);
            if (Number.isNaN(t)) {
                return false;
            }
            return Date.now() - t < EXPECT_NAV_MAX_MS;
        } catch (e) {
            return false;
        }
    }

    function armNavigationFromAnchor(t) {
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
    }

    /* In-app navigation: same-origin <a> / <form> (not new tab, not download). */
    document.addEventListener('click', function (e) {
        armNavigationFromAnchor(e.target && e.target.closest ? e.target.closest('a[href]') : null);
    }, true);

    /* Touch / some browsers: arm before click so pagehide always sees a fresh timestamp. */
    document.addEventListener('pointerdown', function (e) {
        if (e.button != null && e.button !== 0) {
            return;
        }
        armNavigationFromAnchor(e.target && e.target.closest ? e.target.closest('a[href]') : null);
    }, true);

    /* Opening the account menu usually precedes Change password / settings — arm early. */
    document.addEventListener('click', function (e) {
        var t = e.target && e.target.closest ? e.target.closest('.user-menu-btn') : null;
        if (t) {
            setExpectInAppNavigation();
        }
    }, true);

    /* Keyboard / accessibility: refresh intent when focusing a link in app chrome. */
    document.addEventListener(
        'focusin',
        function (e) {
            var t = e.target;
            if (!t || t.tagName !== 'A' || !t.getAttribute || !t.hasAttribute('href')) {
                return;
            }
            if (t.hasAttribute('download')) {
                return;
            }
            var tgt = (t.getAttribute('target') || '').toLowerCase().trim();
            if (tgt === '_blank') {
                return;
            }
            var inMenu =
                (t.closest && !!t.closest('.user-menu-dropdown')) ||
                (t.classList && t.classList.contains('user-menu-item'));
            var inSidebar = t.closest && !!t.closest('.sidebar-nav');
            if (!inMenu && !inSidebar) {
                return;
            }
            try {
                var u = new URL(t.href, location.href);
                if (u.origin === location.origin) {
                    setExpectInAppNavigation();
                }
            } catch (x) {
                void x;
            }
        },
        true
    );

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

    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            return;
        }
        try {
            sessionStorage.removeItem(EXPECT_NAV_KEY);
        } catch (e) { /* */ }
    });

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
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            heartbeat();
        }
    });

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

            var internalNav = isRecentInAppNavigation();

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
