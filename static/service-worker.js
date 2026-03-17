// Service Worker for CI Staff App - Enhanced Offline Mode
const CACHE_NAME = 'ci-staff-v2';
const OFFLINE_URL = '/static/offline.html';

const urlsToCache = [
  '/',
  '/login',
  '/ci/dashboard',
  '/static/manifest.json',
  OFFLINE_URL,
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css'
];

// Install event - cache essential resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache).catch(err => {
          console.log('Cache addAll error:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - Network first, fallback to cache
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    // For POST requests (form submissions), store in IndexedDB if offline
    if (!navigator.onLine) {
      event.respondWith(
        new Response(JSON.stringify({ offline: true, queued: true }), {
          headers: { 'Content-Type': 'application/json' }
        })
      );
      // Store request for later sync
      event.waitUntil(queueRequest(event.request.clone()));
    }
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clone response for caching
        const responseToCache = response.clone();
        
        // Cache successful responses
        if (response.status === 200) {
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        
        return response;
      })
      .catch(() => {
        // Network failed, try cache
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            // If not in cache, show offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
            // For other requests, return error
            return new Response('Offline - resource not cached', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});

// Background Sync - sync queued requests when online
self.addEventListener('sync', event => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncQueuedRequests());
  }
});

// Queue offline requests in IndexedDB
async function queueRequest(request) {
  const db = await openDB();
  const tx = db.transaction('requests', 'readwrite');
  const store = tx.objectStore('requests');
  
  const requestData = {
    url: request.url,
    method: request.method,
    headers: [...request.headers.entries()],
    body: await request.text(),
    timestamp: Date.now()
  };
  
  await store.add(requestData);
}

// Sync queued requests when back online
async function syncQueuedRequests() {
  const db = await openDB();
  const tx = db.transaction('requests', 'readonly');
  const store = tx.objectStore('requests');
  const requests = await store.getAll();
  
  for (const req of requests) {
    try {
      await fetch(req.url, {
        method: req.method,
        headers: new Headers(req.headers),
        body: req.body
      });
      
      // Remove from queue after successful sync
      const deleteTx = db.transaction('requests', 'readwrite');
      await deleteTx.objectStore('requests').delete(req.id);
    } catch (err) {
      console.log('Sync failed for request:', req.url);
    }
  }
}

// Open IndexedDB for storing offline requests
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('ci-staff-offline', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('requests')) {
        db.createObjectStore('requests', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}
