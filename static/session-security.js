// Session security — server ties the cookie to one active login session (ends on Log out
// or optional idle timeout when SESSION_IDLE_LOGOUT is enabled). tab-close-logout.js ends
// the session when the last app tab closes if TAB_CLOSE_AUTO_LOGOUT is on.
// (GET /logout with keepalive); in-app navigations set a short sessionStorage flag so we
// do not sign the user out on every link click.
(function() {
    'use strict';

    if (!document.body.classList.contains('authenticated')) {
        return;
    }

    // Hint browsers not to show stale cached pages for signed-in areas (headers also set on server)
    if (!document.querySelector('meta[http-equiv="Cache-Control"]')) {
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

    // bfcache restore: validate session without a full document reload when still logged in (fast Back/Forward).
    // Use redirect:'manual' so a stale session returns 302 from Flask instead of fetch following login HTML as 200.
    window.addEventListener('pageshow', function (event) {
        if (!event.persisted) {
            return;
        }
        fetch('/api/session_status', {
            method: 'GET',
            credentials: 'same-origin',
            redirect: 'manual',
            headers: {
                Accept: 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            cache: 'no-store'
        })
            .then(function (res) {
                if (res.ok && res.status === 200) {
                    return res.json().then(function (data) {
                        if (data && data.csrf_token) {
                            var m = document.querySelector('meta[name="csrf-token"]');
                            if (m) m.setAttribute('content', data.csrf_token);
                        }
                    }).catch(function () {});
                }
                window.location.reload();
            })
            .catch(function () {});
    });
}());
