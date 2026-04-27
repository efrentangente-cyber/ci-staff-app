// Offline Sync Manager - Auto-download, offline processing, auto-upload
// Real-time, instant UI response (<100ms), background operations

class OfflineSyncManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.isSyncing = false;
    this.downloadQueue = [];
    this.uploadQueue = [];
    this.autoDownloadEnabled = true;
    this.setupEventListeners();
  }

  // Setup online/offline event listeners
  setupEventListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.updateConnectionStatus();
      if (window.DCCCOOutbox && typeof window.DCCCOOutbox.flush === 'function') {
        window.DCCCOOutbox.flush();
      }
      this.syncAll();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.updateConnectionStatus();
    });


    // Initial status
    this.updateConnectionStatus();
  }

  // Update connection status UI
  updateConnectionStatus() {
    const indicator = document.getElementById('offline-indicator');
    if (!indicator) return;

    if (this.isOnline) {
      indicator.classList.remove('offline');
      indicator.classList.add('online');
      indicator.innerHTML = '<i class="bi bi-wifi"></i> Online';
    } else {
      indicator.classList.remove('online');
      indicator.classList.add('offline');
      indicator.innerHTML = '<i class="bi bi-wifi-off"></i> Offline';
    }
    if (typeof window.__dcccoRepaintOfflineIndicator === 'function') {
      window.__dcccoRepaintOfflineIndicator();
    }
  }

  // Download single application with documents
  async downloadApplication(applicationId, showNotification = true) {
    try {
      if (showNotification) {
        this.showToast('Downloading application...', 'info');
      }

      // Fetch application data
      const response = await fetch(`/api/ci_application/${applicationId}`);
      if (!response.ok) throw new Error('Failed to fetch application');

      const data = await response.json();
      const { application, documents } = data;

      // Save application to IndexedDB
      await dbManager.saveApplication(application);

      // Download and save documents (original quality)
      let downloadedDocs = 0;
      for (const doc of documents) {
        try {
          const docResponse = await fetch(`/download_document/${doc.id}`);
          if (docResponse.ok) {
            const blob = await docResponse.blob();
            await dbManager.saveDocument(doc, blob);
            downloadedDocs++;
          }
        } catch (err) {
          console.error(`Failed to download document ${doc.id}:`, err);
        }
      }

      if (showNotification) {
        this.showToast(`Downloaded: ${application.member_name} (${downloadedDocs} documents)`, 'success');
      }

      return true;
    } catch (error) {
      console.error('Download error:', error);
      if (showNotification) {
        this.showToast('Download failed', 'danger');
      }
      return false;
    }
  }

  // Auto-download all new applications
  async autoDownloadApplications() {
    if (!this.isOnline || !this.autoDownloadEnabled) return;

    try {
      // Fetch all assigned applications
      const response = await fetch('/api/ci_applications');
      if (!response.ok) return;

      const applications = await response.json();
      
      // Get already downloaded IDs
      const downloaded = await dbManager.getAllApplications();
      const downloadedIds = new Set(downloaded.map(app => app.id));

      // Find new applications
      const newApps = applications.filter(app => 
        !downloadedIds.has(app.id) && 
        app.status === 'assigned_to_ci'
      );

      if (newApps.length === 0) return;

      this.showToast(`Auto-downloading ${newApps.length} new applications...`, 'info');

      // Download in parallel (max 3 at a time for speed)
      const batchSize = 3;
      for (let i = 0; i < newApps.length; i += batchSize) {
        const batch = newApps.slice(i, i + batchSize);
        await Promise.all(batch.map(app => 
          this.downloadApplication(app.id, false)
        ));
      }

      this.showToast(`Downloaded ${newApps.length} applications`, 'success');
      this.updateStorageInfo();
      
      // Refresh dashboard if visible
      if (window.location.pathname.includes('/ci/dashboard')) {
        this.refreshDashboard();
      }
    } catch (error) {
      console.error('Auto-download error:', error);
    }
  }

  // Upload completed checklist
  async uploadChecklist(checklistId) {
    try {
      const checklists = await dbManager.getPendingChecklists();
      const checklist = checklists.find(c => c.id === checklistId);
      
      if (!checklist) {
        throw new Error('Checklist not found');
      }

      // Prepare form data
      const formData = new FormData();
      formData.append('checklist_data', JSON.stringify(checklist.data));
      formData.append('ci_signature', checklist.signature);
      formData.append('ci_latitude', checklist.latitude || '');
      formData.append('ci_longitude', checklist.longitude || '');

      // Upload
      const response = await fetch(`/submit_ci_checklist/${checklist.application_id}`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Upload failed');

      // Mark as uploaded
      await dbManager.markChecklistUploaded(checklistId);
      
      this.showToast('Checklist uploaded successfully', 'success');
      return true;
    } catch (error) {
      console.error('Upload error:', error);
      this.showToast('Upload failed - will retry when online', 'warning');
      return false;
    }
  }

  // Sync all pending uploads
  async syncAll() {
    if (!this.isOnline || this.isSyncing) return;

    this.isSyncing = true;
    this.showToast('Syncing...', 'info');

    try {
      // Upload pending checklists
      const pending = await dbManager.getPendingChecklists();
      let uploaded = 0;

      for (const checklist of pending) {
        const success = await this.uploadChecklist(checklist.id);
        if (success) uploaded++;
      }

      // Auto-download new applications
      await this.autoDownloadApplications();

      // Cleanup old data
      const deleted = await dbManager.cleanupOldChecklists();

      if (uploaded > 0 || deleted > 0) {
        this.showToast(`Sync complete: ${uploaded} uploaded, ${deleted} cleaned`, 'success');
      }

      this.updateStorageInfo();
    } catch (error) {
      console.error('Sync error:', error);
    } finally {
      this.isSyncing = false;
    }
  }

  // Save checklist offline (instant, <100ms)
  async saveChecklistOffline(applicationId, checklistData, signature, latitude, longitude) {
    try {
      // Save to IndexedDB immediately (instant)
      const id = await dbManager.saveChecklist({
        application_id: applicationId,
        data: checklistData,
        signature: signature,
        latitude: latitude,
        longitude: longitude
      });

      this.showToast('Saved offline - will upload when online', 'success');

      // Try to upload immediately if online
      if (this.isOnline) {
        setTimeout(() => this.uploadChecklist(id), 100);
      }

      return id;
    } catch (error) {
      console.error('Save offline error:', error);
      this.showToast('Failed to save offline', 'danger');
      throw error;
    }
  }

  // Load application from IndexedDB (for offline viewing)
  async loadApplicationOffline(applicationId) {
    try {
      const application = await dbManager.getApplication(applicationId);
      const documents = await dbManager.getDocuments(applicationId);

      return {
        application,
        documents: documents.map(doc => ({
          ...doc,
          url: URL.createObjectURL(doc.blob)
        }))
      };
    } catch (error) {
      console.error('Load offline error:', error);
      return null;
    }
  }

  // Update storage info display - REMOVED
  async updateStorageInfo() {
    // Storage info display has been removed from UI
  }

  // Refresh dashboard with offline data
  async refreshDashboard() {
    const applications = await dbManager.getAllApplications();
    const pending = await dbManager.getPendingChecklists();

    // Emit custom event for dashboard to update
    window.dispatchEvent(new CustomEvent('offline-data-updated', {
      detail: { applications, pending }
    }));
  }

  // Show toast notification
  showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show offline-toast`;
    toast.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      z-index: 9999;
      min-width: 300px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.innerHTML = `
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      ${message}
    `;

    document.body.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  // Download all pending applications (manual trigger)
  async downloadAllPending() {
    if (!this.isOnline) {
      this.showToast('Cannot download while offline', 'warning');
      return;
    }

    this.showToast('Downloading all pending applications...', 'info');
    await this.autoDownloadApplications();
  }

  // Clear all offline data (for testing)
  async clearAllData() {
    if (confirm('Clear all offline data? This cannot be undone.')) {
      await dbManager.clearAll();
      this.showToast('All offline data cleared', 'success');
      this.updateStorageInfo();
      this.refreshDashboard();
    }
  }
}

// Initialize sync manager
const syncManager = new OfflineSyncManager();
window.syncManager = syncManager;

// Auto-sync every 5 minutes when online
setInterval(() => {
  if (syncManager.isOnline) {
    syncManager.syncAll();
  }
}, 5 * 60 * 1000);

// Initial sync on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => syncManager.syncAll(), 1000);
  });
} else {
  setTimeout(() => syncManager.syncAll(), 1000);
}

// Request persistent storage on load
dbManager.requestPersistentStorage().then(granted => {
  if (granted) {
    console.log('✓ Persistent storage granted - data will not be cleared');
  } else {
    console.warn('⚠ Persistent storage denied - data may be cleared by browser');
  }
});
