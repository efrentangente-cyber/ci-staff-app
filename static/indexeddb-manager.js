// IndexedDB Manager for Offline CI Application Storage
// Supports 300+ applications with original quality photos

const DB_NAME = 'ci-staff-offline';
const DB_VERSION = 3;
const STORES = {
  applications: 'applications',
  documents: 'documents',
  checklists: 'checklists',
  pending: 'pending'
};

class IndexedDBManager {
  constructor() {
    this.db = null;
  }

  // Open database connection
  async openDB() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Applications store
        if (!db.objectStoreNames.contains(STORES.applications)) {
          const appStore = db.createObjectStore(STORES.applications, { keyPath: 'id' });
          appStore.createIndex('status', 'status', { unique: false });
          appStore.createIndex('downloaded_at', 'downloaded_at', { unique: false });
        }

        // Documents store (photos, PDFs at original quality)
        if (!db.objectStoreNames.contains(STORES.documents)) {
          const docStore = db.createObjectStore(STORES.documents, { keyPath: 'id', autoIncrement: true });
          docStore.createIndex('loan_application_id', 'loan_application_id', { unique: false });
        }

        // Checklists store (completed CI checklists pending upload)
        if (!db.objectStoreNames.contains(STORES.checklists)) {
          const checklistStore = db.createObjectStore(STORES.checklists, { keyPath: 'id', autoIncrement: true });
          checklistStore.createIndex('application_id', 'application_id', { unique: false });
          checklistStore.createIndex('completed_at', 'completed_at', { unique: false });
          checklistStore.createIndex('uploaded', 'uploaded', { unique: false });
        }

        // Pending requests store (for background sync)
        if (!db.objectStoreNames.contains(STORES.pending)) {
          db.createObjectStore(STORES.pending, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  // Request persistent storage (no limits)
  async requestPersistentStorage() {
    if (navigator.storage && navigator.storage.persist) {
      const isPersisted = await navigator.storage.persist();
      console.log(`Persistent storage: ${isPersisted ? 'granted' : 'denied'}`);
      return isPersisted;
    }
    return false;
  }

  // Get storage estimate
  async getStorageEstimate() {
    if (navigator.storage && navigator.storage.estimate) {
      const estimate = await navigator.storage.estimate();
      return {
        usage: estimate.usage,
        quota: estimate.quota,
        usageInMB: (estimate.usage / (1024 * 1024)).toFixed(2),
        quotaInMB: (estimate.quota / (1024 * 1024)).toFixed(2),
        percentUsed: ((estimate.usage / estimate.quota) * 100).toFixed(2)
      };
    }
    return null;
  }

  // Save application (with all data)
  async saveApplication(application) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.applications, 'readwrite');
      const store = tx.objectStore(STORES.applications);
      
      const appData = {
        ...application,
        downloaded_at: new Date().toISOString(),
        offline_status: 'downloaded'
      };
      
      const request = store.put(appData);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Save document (original quality, no compression)
  async saveDocument(document, blob) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.documents, 'readwrite');
      const store = tx.objectStore(STORES.documents);
      
      const docData = {
        id: document.id,
        loan_application_id: document.loan_application_id,
        file_name: document.file_name,
        file_path: document.file_path,
        uploaded_at: document.uploaded_at,
        blob: blob, // Store original blob
        size: blob.size,
        type: blob.type
      };
      
      const request = store.put(docData);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get all applications
  async getAllApplications() {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.applications, 'readonly');
      const store = tx.objectStore(STORES.applications);
      const request = store.getAll();
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get application by ID
  async getApplication(id) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.applications, 'readonly');
      const store = tx.objectStore(STORES.applications);
      const request = store.get(id);
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get documents for application
  async getDocuments(applicationId) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.documents, 'readonly');
      const store = tx.objectStore(STORES.documents);
      const index = store.index('loan_application_id');
      const request = index.getAll(applicationId);
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Save completed checklist (pending upload)
  async saveChecklist(checklistData) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.checklists, 'readwrite');
      const store = tx.objectStore(STORES.checklists);
      
      const data = {
        ...checklistData,
        completed_at: new Date().toISOString(),
        uploaded: false
      };
      
      const request = store.add(data);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get pending checklists (not uploaded)
  async getPendingChecklists() {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.checklists, 'readonly');
      const store = tx.objectStore(STORES.checklists);
      const index = store.index('uploaded');
      const request = index.getAll(false);
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Mark checklist as uploaded
  async markChecklistUploaded(id) {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.checklists, 'readwrite');
      const store = tx.objectStore(STORES.checklists);
      const getRequest = store.get(id);
      
      getRequest.onsuccess = () => {
        const data = getRequest.result;
        if (data) {
          data.uploaded = true;
          data.uploaded_at = new Date().toISOString();
          const putRequest = store.put(data);
          putRequest.onsuccess = () => resolve(true);
          putRequest.onerror = () => reject(putRequest.error);
        } else {
          resolve(false);
        }
      };
      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  // Delete old completed checklists (7 days)
  async cleanupOldChecklists() {
    const db = await this.openDB();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.checklists, 'readwrite');
      const store = tx.objectStore(STORES.checklists);
      const index = store.index('completed_at');
      const request = index.openCursor();
      
      let deletedCount = 0;
      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          const data = cursor.value;
          const completedDate = new Date(data.completed_at);
          
          // Delete if uploaded and older than 7 days
          if (data.uploaded && completedDate < sevenDaysAgo) {
            cursor.delete();
            deletedCount++;
          }
          cursor.continue();
        } else {
          resolve(deletedCount);
        }
      };
      request.onerror = () => reject(request.error);
    });
  }

  // Delete application and its documents
  async deleteApplication(id) {
    const db = await this.openDB();
    
    // Delete documents first
    const tx1 = db.transaction(STORES.documents, 'readwrite');
    const docStore = tx1.objectStore(STORES.documents);
    const docIndex = docStore.index('loan_application_id');
    const docRequest = docIndex.openCursor(IDBKeyRange.only(id));
    
    await new Promise((resolve, reject) => {
      docRequest.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };
      docRequest.onerror = () => reject(docRequest.error);
    });
    
    // Delete application
    return new Promise((resolve, reject) => {
      const tx2 = db.transaction(STORES.applications, 'readwrite');
      const appStore = tx2.objectStore(STORES.applications);
      const request = appStore.delete(id);
      
      request.onsuccess = () => resolve(true);
      request.onerror = () => reject(request.error);
    });
  }

  // Count applications
  async countApplications() {
    const db = await this.openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.applications, 'readonly');
      const store = tx.objectStore(STORES.applications);
      const request = store.count();
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Clear all data (for testing)
  async clearAll() {
    const db = await this.openDB();
    const stores = [STORES.applications, STORES.documents, STORES.checklists];
    
    for (const storeName of stores) {
      await new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, 'readwrite');
        const store = tx.objectStore(storeName);
        const request = store.clear();
        
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    }
  }
}

// Export singleton instance
const dbManager = new IndexedDBManager();
window.dbManager = dbManager;
