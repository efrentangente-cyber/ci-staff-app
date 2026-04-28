// Session security — server ties the cookie to one active login session (ends on Log out
// or idle timeout). tab-close-logout.js only maintains a lightweight cross-tab heartbeat map;
// it does not POST /logout on unload (that caused false logouts during normal navigation).
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

    // bfcache: tab restored without a network round-trip — reload so Flask runs enforce_single_active_login.
    // Do NOT fetch /api/session_status on back_forward here: fetch follows redirects as 200 HTML (never 401),
    // and catch() reload caused annoying full refreshes on flaky networks — felt like random logouts / flicker.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            window.location.reload();
        }
    });
}());
