// Session Security - Auto logout on browser close and back navigation
(function() {
    'use strict';

    // Track if user is authenticated
    const isAuthenticated = document.body.classList.contains('authenticated');

    if (isAuthenticated) {
        // Session timeout after 2 hours of inactivity (safe behavior only).
        let inactivityTimer;
        const TIMEOUT_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds
        let intentionalNavigation = false;
        let closeLogoutSent = false;

        function getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.getAttribute('content') : '';
        }

        function markIntentionalNavigation() {
            intentionalNavigation = true;
            setTimeout(function() {
                intentionalNavigation = false;
            }, 3000);
        }

        document.addEventListener('click', function(event) {
            const link = event.target && event.target.closest ? event.target.closest('a[href]') : null;
            if (!link) return;

            const href = link.getAttribute('href') || '';
            if (
                !href ||
                href.startsWith('#') ||
                href.startsWith('javascript:') ||
                link.target === '_blank' ||
                link.hasAttribute('download')
            ) {
                return;
            }

            try {
                const nextUrl = new URL(link.href, window.location.href);
                if (nextUrl.origin === window.location.origin) {
                    markIntentionalNavigation();
                }
            } catch (e) {}
        }, true);

        document.addEventListener('submit', function(event) {
            if (event.target && event.target.matches('form')) {
                markIntentionalNavigation();
            }
        }, true);

        function sendCloseLogout() {
            if (closeLogoutSent || intentionalNavigation) {
                return;
            }
            closeLogoutSent = true;

            const csrfToken = getCsrfToken();
            const data = new FormData();
            if (csrfToken) {
                data.append('csrf_token', csrfToken);
            }
            data.append('reason', 'browser_closed');

            if (navigator.sendBeacon) {
                navigator.sendBeacon('/logout', data);
                return;
            }

            fetch('/logout', {
                method: 'POST',
                body: data,
                credentials: 'same-origin',
                keepalive: true,
                headers: csrfToken ? {'X-CSRFToken': csrfToken} : {}
            }).catch(function() {});
        }

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

        // Best-effort security: when the tab/browser is closed, clear the server session.
        // Normal in-system navigation is skipped by intentionalNavigation above.
        window.addEventListener('pagehide', function() {
            sendCloseLogout();
        });
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
