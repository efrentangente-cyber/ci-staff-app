// ═══════════════════════════════════════════════════════════════════
// INDEXEDDB MANAGER - High-Performance Offline Storage
// ═══════════════════════════════════════════════════════════════════

const DB_NAME = 'ci-staff-offline';
/** Must be >= any DB already on the device; lower open() version throws VersionError. Keep in sync with deployment bumps. */
const DB_VERSION = 3;
const CLEANUP_DAYS = 7;

class IndexedDBManager {
    constructor() {
        this.db = null;
        this.initPromise = null;
    }

    // Initialize database with persistent storage
    async init() {
        if (this.initPromise) return this.initPromise;
        
        this.initPromise = new Promise(async (resolve, reject) => {
            try {
                // Request persistent storage (unlimited)
                if (navigator.storage && navigator.storage.persist) {
                    const isPersisted = await navigator.storage.persist();
                    console.log('✅ Persistent storage:', isPersisted ? 'GRANTED' : 'DENIED');
                }

                const request = indexedDB.open(DB_NAME, DB_VERSION);

                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    this.db = request.result;
                    console.log('✅ IndexedDB initialized');
                    resolve(this.db);
                };

                request.onupgradeneeded = (event) => {
                    const db = event.target.result;

                    // Store 1: Downloaded Applications (300+ capacity)
                    if (!db.objectStoreNames.contains('applications')) {
                        const appStore = db.createObjectStore('applications', { keyPath: 'id' });
                        appStore.createIndex('status', 'status', { unique: false });
                        appStore.createIndex('downloaded_at', 'downloaded_at', { unique: false });
                        appStore.createIndex('member_name', 'member_name', { unique: false });
                    }

                    // Store 2: Completed Checklists (pending upload)
                    if (!db.objectStoreNames.contains('completed_checklists')) {
                        const checklistStore = db.createObjectStore('completed_checklists', { keyPath: 'id', autoIncrement: true });
                        checklistStore.createIndex('application_id', 'application_id', { unique: false });
                        checklistStore.createIndex('upload_status', 'upload_status', { unique: false });
                        checklistStore.createIndex('completed_at', 'completed_at', { unique: false });
                        checklistStore.createIndex('retry_count', 'retry_count', { unique: false });
                    }

                    // Store 3: Sync Queue (failed uploads)
                    if (!db.objectStoreNames.contains('sync_queue')) {
                        const syncStore = db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
                        syncStore.createIndex('timestamp', 'timestamp', { unique: false });
                        syncStore.createIndex('retry_count', 'retry_count', { unique: false });
                    }

                };
            } catch (error) {
                reject(error);
            }
        });

        return this.initPromise;
    }

    // ═══════════════════════════════════════════════════════════════════
    // APPLICATIONS STORE - Download & Retrieve
    // ═══════════════════════════════════════════════════════════════════

    // Save single application (< 50ms)
    async saveApplication(appData) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['applications'], 'readwrite');
            const store = transaction.objectStore('applications');
            
            const data = {
                id: appData.id,
                member_name: appData.member_name,
                loan_amount: appData.loan_amount,
                loan_type: appData.loan_type,
                status: appData.status,
                all_application_data: appData, // Full JSON
                photos: appData.photos || [], // Image blobs (subset of document_attachments)
                document_attachments: appData.document_attachments || [], // All loan-package files offline
                downloaded_at: new Date().toISOString()
            };

            const request = store.put(data);
            request.onsuccess = () => resolve(data);
            request.onerror = () => reject(request.error);
        });
    }

    // Bulk save applications (parallel, < 5s for 300 apps)
    async saveApplicationsBulk(appsArray) {
        await this.init();
        const promises = appsArray.map(app => this.saveApplication(app));
        return Promise.all(promises);
    }

    // Get all applications (< 100ms)
    async getAllApplications() {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['applications'], 'readonly');
            const store = transaction.objectStore('applications');
            const request = store.getAll();
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Get single application (< 50ms)
    async getApplication(id) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['applications'], 'readonly');
            const store = transaction.objectStore('applications');
            const request = store.get(id);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Delete application
    async deleteApplication(id) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['applications'], 'readwrite');
            const store = transaction.objectStore('applications');
            const request = store.delete(id);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // COMPLETED CHECKLISTS STORE - Save & Upload Queue
    // ═══════════════════════════════════════════════════════════════════

    // Save completed checklist (< 100ms, instant feedback)
    async saveCompletedChecklist(checklistData) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readwrite');
            const store = transaction.objectStore('completed_checklists');
            
            const data = {
                application_id: checklistData.application_id,
                checklist_data: checklistData.data,
                photos: checklistData.photos || [], // Original quality blobs
                signature: checklistData.signature, // Blob
                gps_location: checklistData.gps_location,
                completed_at: new Date().toISOString(),
                upload_status: 'pending',
                retry_count: 0
            };

            const request = store.add(data);
            request.onsuccess = () => resolve({ id: request.result, ...data });
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Queue a completed CI interview (same payload as online POST + /api/ci/complete_interview).
     * Uses client_request_id (UUID) for idempotent server apply.
     */
    async savePendingInterviewComplete({ applicationId, ciNotes, checklistDataStr, photoBlobs, clientRequestId }) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readwrite');
            const store = transaction.objectStore('completed_checklists');
            const data = {
                kind: 'interview_v2',
                application_id: applicationId,
                ci_notes: ciNotes || '',
                checklist_data_str: checklistDataStr,
                photos: photoBlobs || [],
                client_request_id: clientRequestId,
                completed_at: new Date().toISOString(),
                upload_status: 'pending',
                retry_count: 0
            };
            const request = store.add(data);
            request.onsuccess = () => resolve({ id: request.result, ...data });
            request.onerror = () => reject(request.error);
        });
    }

    // Get all pending checklists
    async getPendingChecklists() {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readonly');
            const store = transaction.objectStore('completed_checklists');
            const index = store.index('upload_status');
            const request = index.getAll('pending');
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /** Pending + failed (for automatic retry; cap retries via retry_count) */
    async getPendingAndRetryableChecklists() {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readonly');
            const store = transaction.objectStore('completed_checklists');
            const request = store.getAll();
            request.onsuccess = () => {
                const rows = request.result || [];
                const out = rows.filter(
                    (r) =>
                        (r.upload_status === 'pending' || r.upload_status === 'failed') &&
                        (r.retry_count || 0) < 10
                );
                out.sort(
                    (a, b) =>
                        new Date(a.completed_at || 0) - new Date(b.completed_at || 0)
                );
                resolve(out);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Update checklist upload status
    async updateChecklistStatus(id, status, retryCount = 0) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readwrite');
            const store = transaction.objectStore('completed_checklists');
            
            const getRequest = store.get(id);
            getRequest.onsuccess = () => {
                const data = getRequest.result;
                if (data) {
                    data.upload_status = status;
                    data.retry_count = retryCount;
                    const putRequest = store.put(data);
                    putRequest.onsuccess = () => resolve(data);
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    reject(new Error('Checklist not found'));
                }
            };
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    // Delete uploaded checklist
    async deleteChecklist(id) {
        await this.init();
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readwrite');
            const store = transaction.objectStore('completed_checklists');
            const request = store.delete(id);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // CLEANUP - Auto-delete after 7 days
    // ═══════════════════════════════════════════════════════════════════

    async cleanupOldData() {
        await this.init();
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - CLEANUP_DAYS);
        const cutoffTime = sevenDaysAgo.toISOString();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['completed_checklists'], 'readwrite');
            const store = transaction.objectStore('completed_checklists');
            const index = store.index('completed_at');
            const request = index.openCursor();

            let deletedCount = 0;

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const data = cursor.value;
                    // Delete if uploaded and older than 7 days
                    if (data.upload_status === 'uploaded' && data.completed_at < cutoffTime) {
                        cursor.delete();
                        deletedCount++;
                    }
                    cursor.continue();
                } else {
                    console.log(`🗑️ Cleaned up ${deletedCount} old checklists`);
                    resolve(deletedCount);
                }
            };

            request.onerror = () => reject(request.error);
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // STORAGE STATUS
    // ═══════════════════════════════════════════════════════════════════

    async getStorageStatus() {
        await this.init();
        
        const apps = await this.getAllApplications();
        const pending = await this.getPendingAndRetryableChecklists();

        let storageEstimate = { usage: 0, quota: 0 };
        if (navigator.storage && navigator.storage.estimate) {
            storageEstimate = await navigator.storage.estimate();
        }

        return {
            applications_count: apps.length,
            pending_checklists: pending.length,
            storage_used_mb: (storageEstimate.usage / (1024 * 1024)).toFixed(2),
            storage_quota_mb: (storageEstimate.quota / (1024 * 1024)).toFixed(2),
            storage_percent: ((storageEstimate.usage / storageEstimate.quota) * 100).toFixed(1)
        };
    }

    // Check if storage is critically low
    async isStorageCriticallyLow() {
        if (navigator.storage && navigator.storage.estimate) {
            const estimate = await navigator.storage.estimate();
            const percentUsed = (estimate.usage / estimate.quota) * 100;
            return percentUsed > 90; // Warn if > 90% used
        }
        return false;
    }
}

// Export singleton instance
const dbManager = new IndexedDBManager();
window.dbManager = dbManager;
