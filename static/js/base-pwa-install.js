(function () {
    if ('serviceWorker' in navigator) {
        var registerServiceWorker = function () {
            navigator.serviceWorker.register('/service-worker.js?v=24-parity-sw').catch(function () {});
        };
        if ('requestIdleCallback' in window) {
            requestIdleCallback(registerServiceWorker, { timeout: 3000 });
        } else {
            window.addEventListener('load', function () {
                setTimeout(registerServiceWorker, 800);
            });
        }
    }

    var deferredPrompt;
    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        deferredPrompt = e;
        var pr = document.getElementById('installPrompt');
        if (pr) pr.classList.remove('d-none');
    });

    document.getElementById('installBtn')?.addEventListener('click', async function () {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
        document.getElementById('installPrompt')?.classList.add('d-none');
    });
})();
