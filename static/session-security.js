// Session security — server ties the cookie to one active login session (ends on Log out
// or idle timeout). tab-close-logout.js posts /logout only when the last app tab closes (tab X),
// not during in-app navigation (links/forms are detected to avoid false logouts).
(function() {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    // Hint browsers not to show stale cached pages for signed-in areas (headers also set on server)
    const metaNoCache = document.createElement('meta');
    metaNoCache.httpEquiv = 'Cache-Control';
    metaNoCache.content = 'no-cache, no-store, must-revalidate';
    document.head.appendChild(metaNoCache);

    const metaPragma = document.createElement('meta');
    metaPragma.httpEquiv = 'Pragma';
    metaPragma.content = 'no-cache';
    document.head.appendChild(metaPragma);

    const metaExpires = document.createElement('meta');
    metaExpires.httpEquiv = 'Expires';
    metaExpires.content = '0';
    document.head.appendChild(metaExpires);

    function loginUrl() {
        const m = document.querySelector('meta[name="login-url"]');
        const u = m && m.getAttribute('content');
        return (u && u.trim()) ? u.trim() : '/login';
    }

    function isBackForwardNavigation() {
        try {
            const nav = performance.getEntriesByType('navigation')[0];
            if (nav && nav.type === 'back_forward') {
                return true;
            }
        } catch (e) {}
        try {
            if (performance.navigation && performance.navigation.type === 2) {
                return true;
            }
        } catch (e2) {}
        return false;
    }

    function revalidateSessionAfterHistory() {
        fetch('/api/session_status', { credentials: 'same-origin', cache: 'no-store' })
            .then(function (res) {
                if (res.status === 401) {
                    window.location.replace(loginUrl());
                    return;
                }
                if (!res.ok) {
                    window.location.reload();
                }
            })
            .catch(function () {
                window.location.reload();
            });
    }

    // bfcache: tab restored from memory without a network request — reload for a real response.
    // back/forward without bfcache: still probe the server so an ended session cannot use history
    // to stay on an authenticated URL with a stale document.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            window.location.reload();
            return;
        }
        if (isBackForwardNavigation()) {
            revalidateSessionAfterHistory();
        }
    });
}());
