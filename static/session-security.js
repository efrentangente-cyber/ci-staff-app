// Session Security - Auto logout on browser close and back navigation
(function() {
    'use strict';

    // Track if user is authenticated
    const isAuthenticated = document.body.classList.contains('authenticated');

    if (isAuthenticated) {
        // Session timeout after 2 hours of inactivity (safe behavior only).
        let inactivityTimer;
        const TIMEOUT_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds
        const TAB_ID_KEY = 'dccco_tab_id';
        const TAB_LOCK_KEY = 'dccco_active_tab_lock';
        const TAB_LOCK_TTL_MS = 20000; // 20s stale-window recovery
        const TAB_HEARTBEAT_MS = 5000;

        function newTabId() {
            try {
                if (window.crypto && window.crypto.randomUUID) {
                    return window.crypto.randomUUID();
                }
            } catch (e) {}
            return 'tab_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
        }

        function readLock() {
            try {
                const raw = localStorage.getItem(TAB_LOCK_KEY);
                if (!raw) return null;
                const parsed = JSON.parse(raw);
                if (!parsed || typeof parsed !== 'object') return null;
                if (!parsed.id || !parsed.ts) return null;
                return parsed;
            } catch (e) {
                return null;
            }
        }

        function writeLock(id) {
            const payload = {id: id, ts: Date.now()};
            try {
                localStorage.setItem(TAB_LOCK_KEY, JSON.stringify(payload));
            } catch (e) {}
        }

        function claimOrValidateTab() {
            const tabId = sessionStorage.getItem(TAB_ID_KEY) || newTabId();
            sessionStorage.setItem(TAB_ID_KEY, tabId);

            const existing = readLock();
            const now = Date.now();
            const isStale = !existing || (now - Number(existing.ts || 0) > TAB_LOCK_TTL_MS);

            if (isStale || existing.id === tabId) {
                writeLock(tabId);
                return tabId;
            }

            // Another tab is currently active: show login screen in this tab
            // without logging out the processing tab.
            window.location.replace('/login');
            return null;
        }

        const activeTabId = claimOrValidateTab();
        if (!activeTabId) {
            return;
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

        const heartbeat = setInterval(function() {
            const current = readLock();
            if (!current || current.id === activeTabId) {
                writeLock(activeTabId);
                return;
            }
            // If another tab has taken control, this tab should go to login.
            window.location.replace('/login');
        }, TAB_HEARTBEAT_MS);

        window.addEventListener('beforeunload', function() {
            clearInterval(heartbeat);
            const current = readLock();
            if (current && current.id === activeTabId) {
                try {
                    localStorage.removeItem(TAB_LOCK_KEY);
                } catch (e) {}
            }
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
