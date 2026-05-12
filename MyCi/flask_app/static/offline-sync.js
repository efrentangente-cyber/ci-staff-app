// ═══════════════════════════════════════════════════════════════════
// OFFLINE SYNC MANAGER - Real-time, Zero-delay Sync
// ═══════════════════════════════════════════════════════════════════

const CI_STAFF_OFFLINE_DB = 'CIStaffOfflineDB';
const CI_STAFF_OFFLINE_DB_VERSION = 1;

/**
 * Same shape as base.html → serverApplications. Android WebView loads offline.html with
 * HTTPS base URL so it reads this DB; ci-staff-offline (indexeddb-manager) is separate.
 */
/**
 * Prefetch main CI HTML so the Service Worker caches the same bundles as online
 * (wizard + interview page). Safe to call after each successful app download.
 */
async function warmCachesForAssignedApp(appId) {
    if (appId == null || typeof navigator === 'undefined' || !navigator.onLine) {
        return;
    }
    const paths = [`/ci/application/${appId}`, `/ci/checklist/${appId}`];
    for (const path of paths) {
        try {
            const res = await fetch(path, {
                credentials: 'include',
                mode: 'same-origin',
                cache: 'default',
            });
            if (!res.ok) {
                console.warn('[offline-sync] warmCaches non-OK', path, res.status);
            }
        } catch (e) {
            console.warn('[offline-sync] warmCaches', path, e);
        }
    }
}

async function mirrorToCiStaffOfflineDB(appRow) {
    if (!appRow || appRow.id == null) return;
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(CI_STAFF_OFFLINE_DB, CI_STAFF_OFFLINE_DB_VERSION);
        request.onerror = () => reject(request.error);
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('serverApplications')) {
                const store = db.createObjectStore('serverApplications', { keyPath: 'serverId' });
                store.createIndex('status', 'status', { unique: false });
                store.createIndex('downloadedAt', 'downloadedAt', { unique: false });
            }
        };
        request.onsuccess = () => {
            const db = request.result;
            try {
                const tx = db.transaction(['serverApplications'], 'readwrite');
                const store = tx.objectStore('serverApplications');
                store.put({
                    serverId: appRow.id,
                    memberName: appRow.member_name,
                    memberAddress: appRow.member_address,
                    loanAmount: appRow.loan_amount,
                    loanPurpose: appRow.loan_purpose || '',
                    status: appRow.status,
                    submittedAt: appRow.submitted_at,
                    downloadedAt: new Date().toISOString()
                });
                tx.oncomplete = () => resolve();
                tx.onerror = () => reject(tx.error);
            } catch (e) {
                reject(e);
            }
        };
    });
}

class OfflineSyncManager {
    constructor() {
        this.isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
        this.isSyncing = false;
        this.syncInProgress = false;
        this.downloadInProgress = false;
        this.listeners = [];
        
        this.init();
    }

    /** WebView often has a stale `navigator.onLine`; refresh before download/sync decisions. */
    refreshConnectivity() {
        if (typeof navigator === 'undefined') {
            return;
        }
        this.isOnline = navigator.onLine;
    }

    // Initialize event listeners
    init() {
        // Connection detection
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        document.addEventListener('visibilitychange', () => {
            this.refreshConnectivity();
            if (!document.hidden && this.isOnline) {
                this.autoSync();
                setTimeout(() => this.autoDownloadNewApplications(), 1000);
            }
        });

        // Initial auto-download if online (runs immediately on load)
        if (this.isOnline) {
            setTimeout(() => this.autoDownloadNewApplications(), 500);
        }

        // Periodic check for new applications every 5 minutes
        setInterval(() => {
            if (this.isOnline && !document.hidden) {
                this.autoDownloadNewApplications();
            }
        }, 300000); // 5 minutes
    }

    // ═══════════════════════════════════════════════════════════════════
    // CONNECTION EVENTS
    // ═══════════════════════════════════════════════════════════════════

    handleOnline() {
        console.log('🟢 ONLINE - Connection detected');
        this.isOnline = true;
        this.notifyListeners('online');
        this.updateStatusBanner('online');
        
        // Auto-sync immediately
        setTimeout(() => this.autoSync(), 500);
        
        // Auto-download new applications after sync
        setTimeout(() => this.autoDownloadNewApplications(), 3000);
    }

    handleOffline() {
        console.log('🔴 OFFLINE - No connection');
        this.isOnline = false;
        this.notifyListeners('offline');
        this.updateStatusBanner('offline');
    }

    // ═══════════════════════════════════════════════════════════════════
    // AUTO-DOWNLOAD APPLICATIONS (Parallel, Background)
    // ═══════════════════════════════════════════════════════════════════

    async autoDownloadNewApplications() {
        this.refreshConnectivity();
        if (!this.isOnline || this.downloadInProgress) return;
        if (typeof dbManager === 'undefined') {
            console.warn('offline-sync: dbManager not loaded');
            return;
        }

        try {
            this.downloadInProgress = true;
            this.updateStatusBanner('downloading');

            const response = await fetch('/api/ci_applications', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to fetch /api/ci_applications');
            }

            const apps = await response.json();
            if (!Array.isArray(apps) || apps.length === 0) {
                console.log('✅ No assigned applications to download');
                this.downloadInProgress = false;
                this.updateStatusBanner('online');
                return;
            }

            console.log(`📥 Downloading ${apps.length} applications (detail + mirror)...`);

            const downloadPromises = apps.map(app => this.downloadApplication(app));
            const results = await Promise.allSettled(downloadPromises);

            const successCount = results.filter(r => r.status === 'fulfilled').length;
            const failCount = results.filter(r => r.status === 'rejected').length;

            console.log(`✅ Downloaded ${successCount}/${apps.length} applications`);
            if (failCount > 0) {
                console.warn(`⚠️ ${failCount} downloads failed`);
            }

            if (successCount > 0) {
                this.showNotification('Applications Downloaded',
                    `✓ ${successCount} application(s) available offline`);
            }

            this.notifyListeners('download_complete', { count: successCount });
            this.downloadInProgress = false;
            this.updateStatusBanner('online');

        } catch (error) {
            console.error('❌ Auto-download error:', error);
            this.downloadInProgress = false;
            this.updateStatusBanner('online');
        }
    }

    // Download single application (Flask: GET /api/ci_application/<id>)
    async downloadApplication(app) {
        this.refreshConnectivity();
        try {
            const rawId = app && app.id;
            if (rawId == null || rawId === '') {
                throw new Error('downloadApplication: missing app.id');
            }
            const appId = Number(rawId);
            if (!Number.isFinite(appId)) {
                throw new Error('downloadApplication: invalid app.id');
            }

            const response = await fetch(`/api/ci_application/${appId}`, {
                credentials: 'include'
            });

            if (!response.ok) {
                let hint = '';
                if (response.status === 401 || response.status === 403) {
                    hint = ' Not logged in or session expired — refresh the page and sign in again.';
                } else if (response.status === 404) {
                    hint = ' This case is not assigned to you or was removed.';
                }
                throw new Error(`Server error ${response.status} for application #${appId}.${hint}`);
            }

            const payload = await response.json();
            const row = payload.application;
            if (!row) {
                throw new Error(`No application row for ${appId}`);
            }

            const documents = Array.isArray(payload.documents) ? payload.documents : [];
            const fullData = { ...row, documents };

            function isImageFileName(name) {
                if (!name || typeof name !== 'string') return false;
                return /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(name.trim());
            }

            /** Every /download/<id> blob (images + PDFs) — IndexedDB + SW cache for offline parity with online. */
            const photoBlobs = [];
            const documentAttachments = [];
            for (let i = 0; i < documents.length; i++) {
                const doc = documents[i];
                if (!doc || doc.id == null) continue;
                try {
                    const dr = await fetch(`/download/${doc.id}`, {
                        method: 'GET',
                        credentials: 'include',
                        cache: 'default',
                        mode: 'same-origin'
                    });
                    if (!dr.ok) {
                        console.warn(`[offline-sync] download doc ${doc.id} failed`, dr.status);
                        continue;
                    }
                    const blob = await dr.blob();
                    if (blob && blob.size) {
                        documentAttachments.push({
                            id: doc.id,
                            file_name: doc.file_name || '',
                            blob,
                        });
                        if (isImageFileName(doc.file_name || '')) {
                            photoBlobs.push(blob);
                        }
                    }
                } catch (e) {
                    console.warn(`[offline-sync] document ${doc && doc.id}`, e);
                }
            }
            fullData.photos = photoBlobs;
            fullData.document_attachments = documentAttachments;
            fullData.id = appId;

            await dbManager.saveApplication(fullData);
            try {
                await mirrorToCiStaffOfflineDB(row);
            } catch (mirrorErr) {
                console.warn('[offline-sync] mirrorToCiStaffOfflineDB (non-fatal):', mirrorErr);
            }
            try {
                await warmCachesForAssignedApp(appId);
            } catch (warmErr) {
                console.warn('[offline-sync] warmCaches (non-fatal):', warmErr);
            }

            return fullData;

        } catch (error) {
            console.error(`❌ Failed to download app ${app && app.id}:`, error);
            throw error;
        }
    }

    // Bulk download all assigned applications
    async downloadAllApplications(progressCallback) {
        this.refreshConnectivity();
        if (!this.isOnline) {
            throw new Error('Cannot download while offline');
        }

        try {
            this.updateStatusBanner('downloading');

            const response = await fetch('/api/ci_applications', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to fetch /api/ci_applications');
            }

            const apps = await response.json();
            if (!Array.isArray(apps) || apps.length === 0) {
                this.updateStatusBanner('online');
                return { success: 0, failed: 0 };
            }

            console.log(`📥 Bulk downloading ${apps.length} applications...`);

            let completed = 0;
            const downloadPromises = apps.map(async (app) => {
                try {
                    await this.downloadApplication(app);
                    completed++;
                    if (progressCallback) {
                        progressCallback(completed, apps.length);
                    }
                    return { success: true, id: app.id };
                } catch (error) {
                    completed++;
                    if (progressCallback) {
                        progressCallback(completed, apps.length);
                    }
                    return { success: false, id: app.id, error };
                }
            });

            const results = await Promise.allSettled(downloadPromises);
            const successCount = results.filter(r => r.status === 'fulfilled' && r.value?.success).length;
            const failCount = apps.length - successCount;

            console.log(`✅ Downloaded ${successCount}/${apps.length} applications`);

            this.updateStatusBanner('online');
            this.notifyListeners('bulk_download_complete', { success: successCount, failed: failCount });

            return { success: successCount, failed: failCount };

        } catch (error) {
            console.error('❌ Bulk download error:', error);
            this.updateStatusBanner('online');
            throw error;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AUTO-UPLOAD COMPLETED CHECKLISTS (Background, Chunked)
    // ═══════════════════════════════════════════════════════════════════

    async autoSync() {
        if (!this.isOnline || this.syncInProgress) return;

        try {
            this.syncInProgress = true;
            this.updateStatusBanner('syncing');

            const pending = await dbManager.getPendingAndRetryableChecklists();

            if (pending.length === 0) {
                console.log('✅ Nothing to sync');
                this.syncInProgress = false;
                this.updateStatusBanner('online');
                return;
            }

            console.log(`🔄 Syncing ${pending.length} completed checklists...`);

            let successCount = 0;
            let failCount = 0;

            // Upload one by one with live progress
            for (let i = 0; i < pending.length; i++) {
                const checklist = pending[i];
                
                try {
                    // Update status banner with progress
                    this.updateStatusBanner('syncing', `Uploading ${i + 1}/${pending.length}`);

                    await this.uploadChecklist(checklist);
                    
                    // Mark as uploaded
                    await dbManager.updateChecklistStatus(checklist.id, 'uploaded');
                    successCount++;

                    console.log(`✅ Uploaded checklist ${i + 1}/${pending.length}`);

                } catch (error) {
                    console.error(`❌ Failed to upload checklist ${checklist.id}:`, error);
                    
                    // Increment retry count
                    const retryCount = (checklist.retry_count || 0) + 1;
                    await dbManager.updateChecklistStatus(checklist.id, 'failed', retryCount);
                    failCount++;
                }
            }

            console.log(`✅ Sync complete: ${successCount} uploaded, ${failCount} failed`);

            // Show notification
            if (successCount > 0) {
                this.showNotification('Sync Complete', 
                    `✓ ${successCount} checklists uploaded successfully`);
            }

            this.syncInProgress = false;
            this.updateStatusBanner('online');
            this.notifyListeners('sync_complete', { success: successCount, failed: failCount });

            // Auto-cleanup old data
            await dbManager.cleanupOldData();

        } catch (error) {
            console.error('❌ Auto-sync error:', error);
            this.syncInProgress = false;
            this.updateStatusBanner('online');
        }
    }

    /** Profile signature as data URL — paired with API /api/ci/complete_interview snapshot behavior. */
    async appendCiSignatureForCompleteInterview(formData) {
        try {
            const r = await fetch('/api/ci/signature_for_interview', { credentials: 'include', cache: 'no-store' });
            const j = await r.json().catch(() => ({}));
            if (j.signature_data_url && typeof j.signature_data_url === 'string') {
                formData.append('signature_data', j.signature_data_url);
            }
        } catch (e) { /* offline / CORS — server still falls back to profile path */ }
    }

    // Upload one pending row (interview / legacy checklist)
    async uploadChecklist(checklist) {
        // New path: same contract as /ci/application POST + client_request_id (idempotent)
        if (checklist.kind === 'interview_v2' && checklist.checklist_data_str != null) {
            const formData = new FormData();
            formData.append('application_id', String(checklist.application_id));
            formData.append('ci_notes', checklist.ci_notes != null ? checklist.ci_notes : '');
            formData.append('checklist_data', checklist.checklist_data_str);
            formData.append('client_request_id', checklist.client_request_id);
            formData.append('completed_at', checklist.completed_at || new Date().toISOString());
            (checklist.photos || []).forEach((photoBlob, index) => {
                formData.append(`photo_${index}`, photoBlob, `interview_${index}.jpg`);
            });
            await this.appendCiSignatureForCompleteInterview(formData);

            const response = await fetch('/api/ci/complete_interview', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || `Upload failed: ${response.status}`);
            }
            if (data.duplicate) {
                console.log('✓ Idempotent retry — already on server', checklist.client_request_id);
            }
            return data;
        }

        // Legacy: flat checklist JSON for /api/ci/upload_checklist
        const formData = new FormData();
        formData.append('application_id', checklist.application_id);
        formData.append('checklist_data', JSON.stringify(checklist.checklist_data));
        formData.append('gps_location', JSON.stringify(checklist.gps_location));
        formData.append('completed_at', checklist.completed_at);

        if (checklist.photos && checklist.photos.length > 0) {
            checklist.photos.forEach((photoBlob, index) => {
                formData.append(`photo_${index}`, photoBlob, `photo_${index}.jpg`);
            });
        }
        if (checklist.signature) {
            formData.append('signature', checklist.signature, 'signature.png');
        }

        const response = await fetch('/api/ci/upload_checklist', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * Upload pending checklist rows from IndexedDB (ci-staff-offline) → server SQLite.
     * Mirrors each saved app row into CIStaffOfflineDB.serverApplications after download.
     */
    async pushIndexedDBToServer() {
        return this.autoSync();
    }

    /** Pull GET /api/ci_applications + per-app JSON + documents → IndexedDB (+ mirror DB). */
    async pullServerToIndexedDB() {
        return this.autoDownloadNewApplications();
    }

    /**
     * One “Sync” pipeline: flush local uploads first, then download latest assignments.
     * Connects offline (browser IndexedDB) ↔ online (Flask/SQLite) in both directions.
     */
    async fullBidirectionalSync() {
        this.refreshConnectivity();
        if (!this.isOnline) {
            throw new Error('Cannot sync while offline');
        }
        await this.autoSync();
        await this.autoDownloadNewApplications();
    }

    // Manual sync: push queued data, then pull server state (same as tapping “Sync Now”)
    async manualSync() {
        this.refreshConnectivity();
        if (!this.isOnline) {
            throw new Error('Cannot sync while offline');
        }

        return this.fullBidirectionalSync();
    }

    // ═══════════════════════════════════════════════════════════════════
    // STATUS BANNER & NOTIFICATIONS
    // ═══════════════════════════════════════════════════════════════════

    updateStatusBanner(status, message = '') {
        const banner = document.getElementById('offlineStatusBanner');
        if (!banner) return;

        const icons = {
            online: '🟢',
            offline: '🔴',
            syncing: '🟡',
            downloading: '📥'
        };

        const texts = {
            online: 'ONLINE - All data synced',
            offline: 'OFFLINE MODE',
            syncing: message || 'SYNCING...',
            downloading: 'Downloading applications...'
        };

        banner.className = `offline-status-banner status-${status}`;
        banner.innerHTML = `${icons[status]} ${texts[status]}`;
    }

    // Show browser notification
    showNotification(title, body) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: '/static/images/logo.jpg',
                badge: '/static/images/logo.jpg'
            });
        }
    }

    // Request notification permission
    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }
        return Notification.permission === 'granted';
    }

    // ═══════════════════════════════════════════════════════════════════
    // EVENT LISTENERS
    // ═══════════════════════════════════════════════════════════════════

    addEventListener(callback) {
        this.listeners.push(callback);
    }

    notifyListeners(event, data = {}) {
        this.listeners.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Listener error:', error);
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // STORAGE STATUS
    // ═══════════════════════════════════════════════════════════════════

    async getStatus() {
        const storage = await dbManager.getStorageStatus();
        const pending = await dbManager.getPendingAndRetryableChecklists();

        return {
            online: this.isOnline,
            syncing: this.syncInProgress,
            downloading: this.downloadInProgress,
            applications_count: storage.applications_count,
            pending_uploads: pending.length,
            storage_used_mb: storage.storage_used_mb,
            storage_quota_mb: storage.storage_quota_mb,
            storage_percent: storage.storage_percent
        };
    }
}

// Export singleton instance
const syncManager = new OfflineSyncManager();
window.syncManager = syncManager;

/** Stable API for tools / consoles: IndexedDB ⇄ server orchestration */
window.ciDataSync = {
    push: () => syncManager.pushIndexedDBToServer(),
    pull: () => syncManager.pullServerToIndexedDB(),
    full: () => syncManager.fullBidirectionalSync(),
    status: () => syncManager.getStatus(),
};
