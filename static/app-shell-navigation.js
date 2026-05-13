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

    var progressTimer = null;

    function showProgressSoon() {
        if (progressTimer !== null) {
            return;
        }
        progressTimer = window.setTimeout(function () {
            progressTimer = null;
            document.documentElement.classList.add('dccco-turbo-busy');
        }, 140);
    }

    function hideProgress() {
        if (progressTimer !== null) {
            window.clearTimeout(progressTimer);
            progressTimer = null;
        }
        document.documentElement.classList.remove('dccco-turbo-busy');
    }

    document.addEventListener('turbo:before-fetch-request', showProgressSoon);
    document.addEventListener('turbo:load', hideProgress);
    document.addEventListener('turbo:fetch-request-error', hideProgress);
})();
