/* Load synchronously in <head> before paint to avoid dark-mode flash */
(function () {
  if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark-mode-loading');
  }
})();
