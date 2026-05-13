/**
 * Push CI/BI GPS periodically on any CI-staff page except the checklist wizard
 * (wizard uses ci-location-tracker.js at a higher rate with form fields).
 */
(function () {
    'use strict';

    if (!navigator.geolocation) {
        return;
    }

    function postLocation(lat, lng) {
        fetch('/api/update_location', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
            },
            body: JSON.stringify({
                latitude: lat,
                longitude: lng,
                activity: document.hidden ? 'Away' : 'Active',
            }),
        }).catch(function () {});
    }

    function tick() {
        navigator.geolocation.getCurrentPosition(
            function (p) {
                postLocation(p.coords.latitude, p.coords.longitude);
            },
            function () {},
            {
                enableHighAccuracy: false,
                maximumAge: 90000,
                timeout: 22000,
            }
        );
    }

    function boot() {
        if (document.getElementById('ciChecklistForm')) {
            return;
        }
        tick();
        window.setInterval(tick, 55000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
