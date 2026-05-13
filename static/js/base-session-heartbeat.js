(function () {
    if (!sessionStorage.getItem('loginTime')) {
        sessionStorage.setItem('loginTime', Date.now().toString());
    }
    var el = document.getElementById('dccco-session-config');
    var cfg = {};
    if (el) {
        try {
            cfg = JSON.parse(el.textContent || '{}');
        } catch (_e) {
            cfg = {};
        }
    }
    var hbUrl = cfg.heartbeat || '';
    var stUrl = cfg.sessionStatus || '';
    var intervalMs = 60 * 1000;

    function applyCsrfFromPayload(data) {
        if (data && data.csrf_token) {
            var m = document.querySelector('meta[name="csrf-token"]');
            if (m) m.setAttribute('content', data.csrf_token);
        }
    }

    function pullCsrfFromSessionStatus() {
        if (!stUrl) return;
        fetch(stUrl, {
            method: 'GET',
            credentials: 'same-origin',
            headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            cache: 'no-store',
        })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (data && data.ok) applyCsrfFromPayload(data);
            })
            .catch(function () {});
    }

    function sessionHeartbeat() {
        if (!hbUrl) return;
        fetch(hbUrl, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
            },
            cache: 'no-store',
        })
            .then(function (r) { return r.json().catch(function () { return {}; }); })
            .then(function (data) {
                applyCsrfFromPayload(data);
            })
            .catch(function () {});
    }

    setInterval(sessionHeartbeat, intervalMs);
    setInterval(pullCsrfFromSessionStatus, 3 * 60 * 1000);
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            pullCsrfFromSessionStatus();
            sessionHeartbeat();
        }
    });
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(pullCsrfFromSessionStatus, 900);
        setTimeout(sessionHeartbeat, 2400);
    });
    document.addEventListener('turbo:load', function () {
        setTimeout(pullCsrfFromSessionStatus, 120);
        setTimeout(sessionHeartbeat, 650);
    });
})();
