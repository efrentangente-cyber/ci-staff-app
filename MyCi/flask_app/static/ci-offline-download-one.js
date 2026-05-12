/**
 * Save one assigned application (+ documents) into IndexedDB for offline processing.
 * Requires indexeddb-manager.js + offline-sync.js (syncManager, dbManager).
 */
async function ciDownloadApplicationForOffline(applicationId, options) {
    const opts = options || {};
    const btn = opts.button || null;

    if (typeof dbManager === 'undefined' || typeof syncManager === 'undefined') {
        window.alert(
            'Offline storage scripts are still loading. Wait a few seconds and tap Download again.'
        );
        return false;
    }

    const idNum = Number(applicationId);
    if (!Number.isFinite(idNum)) {
        window.alert('Invalid application id. Refresh the page and try again.');
        return false;
    }

    await dbManager.init();

    if (typeof syncManager.refreshConnectivity === 'function') {
        syncManager.refreshConnectivity();
    }

    // Block only when the browser reports offline (syncManager.isOnline can stay wrong in WebView).
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
        window.alert(
            'No network connection. Turn on Wi‑Fi or mobile data, then try Save for offline again.'
        );
        return false;
    }

    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status"></span> Saving…';
    }

    try {
        await syncManager.downloadApplication({ id: idNum });
        if (typeof opts.onSuccess === 'function') {
            opts.onSuccess(idNum);
        }
        return true;
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        window.alert(
            'Download failed. If you are logged in, try refreshing the page.\n\n' + msg
        );
        return false;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = oldHtml;
        }
    }
}

window.ciDownloadApplicationForOffline = ciDownloadApplicationForOffline;
