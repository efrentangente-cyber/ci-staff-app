(function () {
    function showBanner(msg, color, autohide) {
        var ind = document.getElementById('offlineIndicator');
        if (!ind) {
            ind = document.createElement('div');
            ind.id = 'offlineIndicator';
            ind.style.cssText =
                'position:fixed;top:0;left:0;right:0;padding:10px;text-align:center;z-index:9999;font-weight:bold;font-size:14px;';
            document.body.appendChild(ind);
        }
        ind.innerHTML = msg;
        ind.style.background = color;
        ind.style.color = 'white';
        ind.style.display = 'block';
        if (autohide) setTimeout(function () { ind.style.display = 'none'; }, 3000);
    }

    window.addEventListener('offline', function () {
        showBanner(
            '📡 Offline — submits are saved on this device and sent when you reconnect',
            '#f59e0b',
            false
        );
    });

    window.addEventListener('online', function () {
        showBanner('✅ Back online — syncing saved data...', '#10b981', false);
        if (window.DCCCOOutbox && typeof window.DCCCOOutbox.flush === 'function') {
            window.DCCCOOutbox.flush();
        }
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            navigator.serviceWorker.ready
                .then(function (reg) {
                    return reg.sync.register('sync-pending');
                })
                .catch(function (err) {
                    console.log('Background sync registration failed', err);
                });
        }
    });

    if (!navigator.onLine) {
        showBanner(
            '📡 Offline — submits are saved on this device and sent when you reconnect',
            '#f59e0b',
            false
        );
    }
})();
