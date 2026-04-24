// Session Security - Auto logout on browser close and back navigation
(function() {
    'use strict';

    // Track if user is authenticated
    const isAuthenticated = document.body.classList.contains('authenticated');

    if (isAuthenticated) {
        // Session timeout after 2 hours of inactivity (safe behavior only).
        let inactivityTimer;
        const TIMEOUT_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds

        function resetInactivityTimer() {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(function() {
                alert('Your session has expired due to inactivity. Please log in again.');
                // Use full navigation to logout route for reliability.
                window.location.href = '/logout';
            }, TIMEOUT_DURATION);
        }

        // Reset timer on user activity
        ['mousedown', 'keypress', 'scroll', 'touchstart', 'click'].forEach(function(event) {
            document.addEventListener(event, resetInactivityTimer, true);
        });

        // Start the inactivity timer
        resetInactivityTimer();
    }

    // Prevent caching for all authenticated pages
    if (isAuthenticated) {
        // Set cache control headers via meta tags
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
    }
})();
