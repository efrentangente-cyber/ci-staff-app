(function () {
    try {
        if (localStorage.getItem('darkMode') === 'true') {
            document.documentElement.classList.add('dark-mode-loading');
        }
    } catch (_e) {}
})();
