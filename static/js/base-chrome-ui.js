(function () {
    try {
        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
        }
    } catch (_e) {}

    function syncDarkModeToggleIcon() {
        var darkModeIcon = document.getElementById('darkModeIcon');
        var body = document.body;
        if (!darkModeIcon || !body) return;
        if (body.classList.contains('dark-mode')) {
            darkModeIcon.classList.remove('bi-moon-fill');
            darkModeIcon.classList.add('bi-sun-fill');
        } else {
            darkModeIcon.classList.remove('bi-sun-fill');
            darkModeIcon.classList.add('bi-moon-fill');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncDarkModeToggleIcon);
    } else {
        syncDarkModeToggleIcon();
    }
    document.addEventListener('turbo:load', syncDarkModeToggleIcon);

    if (!window.__dcccoDarkToggleDelegationBound) {
        window.__dcccoDarkToggleDelegationBound = true;
        document.addEventListener('click', function (e) {
            var btn = e.target && e.target.closest && e.target.closest('#darkModeToggle');
            if (!btn) return;
            e.preventDefault();
            document.body.classList.toggle('dark-mode');
            localStorage.setItem(
                'darkMode',
                document.body.classList.contains('dark-mode') ? 'true' : 'false'
            );
            syncDarkModeToggleIcon();
        });
    }

    function initUserMenuDropdowns() {
        document.querySelectorAll('.user-menu-container').forEach(function (container) {
            var menuButton = container.querySelector('.user-menu-btn');
            var menuDropdown = container.querySelector('.user-menu-dropdown');

            if (menuButton && menuDropdown) {
                var newButton = menuButton.cloneNode(true);
                menuButton.parentNode.replaceChild(newButton, menuButton);

                newButton.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();

                    document.querySelectorAll('.user-menu-container').forEach(function (c) {
                        var d = c.querySelector('.user-menu-dropdown');
                        var b = c.querySelector('.user-menu-btn');
                        if (d && d !== menuDropdown) {
                            d.classList.remove('show');
                            if (b) b.setAttribute('aria-expanded', 'false');
                        }
                    });

                    menuDropdown.classList.toggle('show');
                    newButton.setAttribute('aria-expanded', menuDropdown.classList.contains('show'));
                });
            }
        });

        if (!window.__dcccoUserMenuOutsideClickBound) {
            window.__dcccoUserMenuOutsideClickBound = true;
            document.addEventListener('click', function (e) {
                if (!e.target.closest('.user-menu-container')) {
                    document.querySelectorAll('.user-menu-dropdown').forEach(function (dropdown) {
                        dropdown.classList.remove('show');
                    });
                    document.querySelectorAll('.user-menu-btn').forEach(function (btn) {
                        btn.setAttribute('aria-expanded', 'false');
                    });
                }
            });
        }

        document.querySelectorAll('.user-menu-btn').forEach(function (btn) {
            if (!btn.getAttribute('aria-label')) btn.setAttribute('aria-label', 'Open account menu');
            btn.setAttribute('aria-haspopup', 'true');
            if (btn.getAttribute('aria-expanded') == null) btn.setAttribute('aria-expanded', 'false');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUserMenuDropdowns);
    } else {
        initUserMenuDropdowns();
    }
    document.addEventListener('turbo:load', initUserMenuDropdowns);
})();
