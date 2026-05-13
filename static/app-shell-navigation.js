/**
 * Hotwired Turbo Drive — SPA-like navigations inside authenticated chrome.
 * Heavy flows stay full-page (logout, login, loan submission wizard, CI checklist wizard).
 */
(function () {
    'use strict';

    if (typeof Turbo === 'undefined') {
        return;
    }

    function needsFullPageVisit(href) {
        try {
            var abs =
                typeof href === 'string'
                    ? new URL(href, window.location.href)
                    : href;
            var p = abs.pathname || '';
            if (p === '/logout' || p === '/login') {
                return true;
            }
            if (p === '/loan/submit') {
                return true;
            }
            if (p === '/ci-tracking') {
                return true;
            }
            if (p.indexOf('/ci/checklist/wizard/') === 0) {
                return true;
            }
            return false;
        } catch (_e) {
            return false;
        }
    }

    document.addEventListener('turbo:before-visit', function (event) {
        var detail = event.detail || {};
        var url = detail.url;
        var href =
            typeof url === 'string'
                ? url
                : url && url.href
                  ? url.href
                  : String(url || '');
        if (needsFullPageVisit(href)) {
            event.preventDefault();
            window.location.href = href;
        }
    });

    /*
     * Turbo 8 link prefetch (hover) issues a second full navigation request.
     * With Gunicorn+eventlet and a small pool, that doubles DB/HTML work and makes
     * real clicks feel sluggish. Drive remains SPA-like; only hover prefetch is off.
     */
    document.addEventListener('turbo:before-prefetch', function (event) {
        event.preventDefault();
    });

    // Intentionally no progress overlay: even a slim rail made sub-second navigations feel "loading".
})();
