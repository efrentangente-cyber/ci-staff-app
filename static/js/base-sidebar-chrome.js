(function () {
    var __dcccoChromePrefetch = {};

    function shouldPrefetchChromeAnchor(a) {
        if (!a || !a.getAttribute || !a.getAttribute('href')) {
            return false;
        }
        if ((a.getAttribute('target') || '').toLowerCase().trim() === '_blank') {
            return false;
        }
        if (a.hasAttribute('download')) {
            return false;
        }
        var raw = String(a.getAttribute('href')).trim();
        if (!raw || raw[0] === '#' || raw.indexOf('mailto:') === 0 || raw.indexOf('tel:') === 0) {
            return false;
        }
        try {
            var u = new URL(a.href, window.location.href);
            if (u.origin !== window.location.origin) {
                return false;
            }
            if (u.pathname === '/logout' || raw.indexOf('logout') === 0 || u.pathname.indexOf('/logout') === 0) {
                return false;
            }
        } catch (_ePath) {
            return false;
        }
        try {
            var c = navigator.connection;
            if (
                c &&
                (c.saveData === true ||
                    (typeof c.effectiveType === 'string' && /^(slow-2g|2g)$/.test(c.effectiveType)))
            ) {
                return false;
            }
        } catch (_eSkip) {}
        return true;
    }

    function injectPrefetch(hrefCanonical) {
        if (__dcccoChromePrefetch[hrefCanonical]) {
            return;
        }
        __dcccoChromePrefetch[hrefCanonical] = 1;
        try {
            var l = document.createElement('link');
            l.rel = 'prefetch';
            l.href = hrefCanonical;
            document.head.appendChild(l);
        } catch (_eLink) {}
    }

    function onChromePointerPrefetch(ev) {
        if (!ev.target || typeof ev.target.closest !== 'function') {
            return;
        }
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) {
            return;
        }
        if (typeof ev.button === 'number' && ev.button !== 0) {
            return;
        }
        if (typeof ev.pointerType === 'string' && ev.pointerType !== 'touch' && !ev.isPrimary) {
            return;
        }
        var a = ev.target.closest('a[href]');
        if (!a) {
            return;
        }
        var inChrome = !!(a.closest('.sidebar-nav') || a.closest('.bottom-nav') || a.closest('.user-menu-dropdown'));
        if (!inChrome) {
            return;
        }
        if (!shouldPrefetchChromeAnchor(a)) {
            return;
        }
        try {
            injectPrefetch(new URL(a.href, window.location.href).href);
        } catch (_eU) {}
    }

    function onChromeHoverPrefetch(ev) {
        if (!ev.target || typeof ev.target.closest !== 'function') {
            return;
        }
        var a = ev.target.closest('a[href]');
        if (
            !a ||
            (!a.closest('.sidebar-nav') && !a.closest('.bottom-nav') && !a.closest('.user-menu-dropdown'))
        ) {
            return;
        }
        if (!shouldPrefetchChromeAnchor(a)) {
            return;
        }
        var key;
        try {
            key = new URL(a.href, window.location.href).href;
        } catch (_err) {
            return;
        }
        if (__dcccoChromePrefetch[key]) {
            return;
        }
        function go() {
            injectPrefetch(key);
        }
        if (window.requestIdleCallback) {
            window.requestIdleCallback(go, { timeout: 2600 });
        } else {
            setTimeout(go, 120);
        }
    }

    function bindSidebarChromePrefetch() {
        var currentPath = window.location.pathname;
        document.querySelectorAll('.sidebar-nav a').forEach(function (link) {
            link.classList.remove('active');
        });
        document.querySelectorAll('.sidebar-nav a').forEach(function (link) {
            var linkPath = new URL(link.href).pathname;
            if (linkPath === currentPath) {
                link.classList.add('active');
            }
            if (currentPath.includes('/dashboard') && link.textContent.trim().includes('Home')) {
                link.classList.add('active');
            }
        });

        var sidebar = document.querySelector('.sidebar-nav');
        if (sidebar) {
            var savedScrollPos = sessionStorage.getItem('sidebarScrollPos');
            if (savedScrollPos) {
                sidebar.scrollTop = parseInt(savedScrollPos, 10);
            }
            if (!window.__dcccoSidebarScrollHooked) {
                window.__dcccoSidebarScrollHooked = true;
                window.addEventListener('pagehide', function () {
                    try {
                        var sb = document.querySelector('.sidebar-nav');
                        if (sb) {
                            sessionStorage.setItem('sidebarScrollPos', String(sb.scrollTop));
                        }
                    } catch (_e2) {}
                });
            }
        }

        var dash = document.querySelector('.dashboard-container');
        if (dash && dash.dataset.dcccoPrefetchBound !== '1') {
            dash.dataset.dcccoPrefetchBound = '1';
            dash.addEventListener('pointerdown', onChromePointerPrefetch, true);
            dash.addEventListener('mouseover', onChromeHoverPrefetch, true);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindSidebarChromePrefetch);
    } else {
        bindSidebarChromePrefetch();
    }
    document.addEventListener('turbo:load', bindSidebarChromePrefetch);
})();
