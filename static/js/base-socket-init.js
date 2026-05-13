(function () {
    if (typeof io !== 'function') return;
    var el = document.getElementById('dccco-socket-boot');
    var cfg = {};
    if (el) {
        try {
            cfg = JSON.parse(el.textContent || '{}');
        } catch (_e) {
            cfg = {};
        }
    }
    if (!window.__dcccoSocket) {
        window.__dcccoSocket = io({
            path: '/socket.io/',
            transports: ['polling', 'websocket'],
            upgrade: true,
            rememberUpgrade: false,
            reconnection: true,
            reconnectionDelay: 800,
            reconnectionDelayMax: 12000,
            reconnectionAttempts: 15,
            timeout: 20000,
        });
    }
    var socket = window.__dcccoSocket;
    if (!socket || socket.__dcccoBaseHandlersBound) {
        try {
            document.dispatchEvent(new CustomEvent('dccco:socket-ready'));
        } catch (_eSd) {}
        return;
    }
    socket.__dcccoBaseHandlersBound = true;
    socket.on('connect', function () {
        socket.emit('join', { room: String(cfg.userId != null ? cfg.userId : '') });
    });
    socket.on('new_notification', function (data) {
        if (!data || data.is_direct_message) return;
        var badge = document.getElementById('notif-count');
        var mobileBadge = document.getElementById('notif-count-mobile');
        var topbarBadge = document.getElementById('notif-count-topbar');
        if (badge) {
            badge.textContent = (parseInt(badge.textContent, 10) || 0) + 1;
            badge.style.display = 'inline';
        }
        if (mobileBadge) {
            mobileBadge.textContent = (parseInt(mobileBadge.textContent, 10) || 0) + 1;
            mobileBadge.style.display = 'inline';
        }
        if (topbarBadge) {
            topbarBadge.textContent = (parseInt(topbarBadge.textContent, 10) || 0) + 1;
            topbarBadge.style.display = 'inline';
        }
        if ('Notification' in window && Notification.permission === 'granted') {
            var title =
                cfg.notifyTitle && String(cfg.notifyTitle).trim()
                    ? String(cfg.notifyTitle)
                    : 'Notification';
            new Notification(title, {
                body: data.message,
                icon: '/static/favicon.png',
            });
        }
    });
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    try {
        document.dispatchEvent(new CustomEvent('dccco:socket-ready'));
    } catch (_eSd) {}
})();
