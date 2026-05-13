(function () {
    function bindAutoDismissAlerts() {
        document
            .querySelectorAll('.auto-dismiss-alert:not([data-dccco-dismiss-bound])')
            .forEach(function (alert) {
                alert.setAttribute('data-dccco-dismiss-bound', '1');
                var cat = (alert.getAttribute('data-alert-cat') || '').toLowerCase();
                var ms =
                    cat === 'danger' || cat === 'warning'
                        ? 10000
                        : cat === 'info'
                          ? 5000
                          : 4000;
                function closeToast() {
                    alert.classList.add('hide');
                    setTimeout(function () {
                        alert.remove();
                    }, 180);
                }
                alert.querySelector('.sweet-toast-close')?.addEventListener('click', closeToast);
                setTimeout(closeToast, ms);
            });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindAutoDismissAlerts);
    } else {
        bindAutoDismissAlerts();
    }
    document.addEventListener('turbo:load', bindAutoDismissAlerts);
})();
