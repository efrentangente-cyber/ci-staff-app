// Session Security - Auto logout on browser close and back navigation
(function() {
    'use strict';
    
    // Generate a unique session ID for this browser tab
    const sessionId = sessionStorage.getItem('sessionId') || Date.now() + '-' + Math.random();
    sessionStorage.setItem('sessionId', sessionId);
    
    // Track if user is authenticated
    const isAuthenticated = document.body.classList.contains('authenticated');
    
    if (isAuthenticated) {
        // Check if link was opened from external source (shared link)
        // If referrer is empty or from different domain, it's likely a shared link
        const isSharedLink = !document.referrer || 
                            (document.referrer && !document.referrer.includes(window.location.hostname));
        
        // Check if this is a fresh page load (not navigation within app)
        const isDirectAccess = window.performance && 
                              window.performance.navigation && 
                              window.performance.navigation.type === 0;
        
        // If link was shared/opened directly, logout and redirect to login
        if (isSharedLink && isDirectAccess) {
            // Check if user just logged in (within last 5 seconds)
            const loginTime = sessionStorage.getItem('loginTime');
            const now = Date.now();
            const justLoggedIn = loginTime && (now - parseInt(loginTime)) < 5000;
            
            if (!justLoggedIn) {
                // This is a shared link - logout and show login page
                sessionStorage.clear();
                fetch('/logout', {
                    method: 'GET',
                    credentials: 'same-origin'
                }).then(() => {
                    window.location.href = '/login?reason=shared_link';
                });
                return; // Stop further execution
            }
        }
        
        // Clear session on browser close (when sessionStorage is cleared)
        window.addEventListener('beforeunload', function(e) {
            // Mark session as ending
            sessionStorage.setItem('sessionEnding', 'true');
        });
        
        // Check if returning from a closed session
        window.addEventListener('load', function() {
            // If sessionStorage was cleared (browser was closed), logout
            if (!sessionStorage.getItem('sessionActive')) {
                // First load after browser open - set as active
                sessionStorage.setItem('sessionActive', 'true');
            }
        });
        
        // Detect back button navigation and logout
        window.addEventListener('pageshow', function(event) {
            // If page is loaded from cache (back button), logout
            if (event.persisted || (window.performance && window.performance.navigation.type === 2)) {
                // User pressed back button
                fetch('/logout', {
                    method: 'GET',
                    credentials: 'same-origin'
                }).then(() => {
                    window.location.href = '/login';
                });
            }
        });
        
        // Prevent caching of authenticated pages
        if (window.history && window.history.pushState) {
            window.history.pushState(null, null, window.location.href);
            window.addEventListener('popstate', function() {
                // User pressed back button - logout
                fetch('/logout', {
                    method: 'GET',
                    credentials: 'same-origin'
                }).then(() => {
                    window.location.href = '/login';
                });
            });
        }
        
        // Session timeout after 2 hours of inactivity
        let inactivityTimer;
        const TIMEOUT_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds
        
        function resetInactivityTimer() {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(function() {
                alert('Your session has expired due to inactivity. Please log in again.');
                fetch('/logout', {
                    method: 'GET',
                    credentials: 'same-origin'
                }).then(() => {
                    window.location.href = '/login';
                });
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
