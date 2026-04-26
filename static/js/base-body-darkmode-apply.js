(function () {
  if (document.documentElement.classList.contains('dark-mode-loading')) {
    document.body.classList.add('dark-mode');
    document.documentElement.classList.remove('dark-mode-loading');
  }
})();
