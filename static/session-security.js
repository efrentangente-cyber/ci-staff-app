// Session security — server controls sign-out (single device + idle timeout). No forced
// client logout or "single browser tab" lock, so users can work across tabs, read docs,
// and complete long checklists without being interrupted.
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

    // Browsers (especially Chromium) can restore this tab from the back/forward cache
    // without hitting the network. A restored snapshot could show a stale signed-in
    // UI or cached form data after sign-out. Force a reload so the server re-checks
    // the session and headers apply. You cannot fully disable the toolbar Back button;
    // revalidation is the correct mitigation.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            window.location.reload();
        }
    });
}());
