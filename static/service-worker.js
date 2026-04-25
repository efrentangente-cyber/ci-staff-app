// DCCCO CI Staff App - Service Worker v6 - Offline PWA with Auto-sync
const CACHE_NAME = 'dccco-staff-v6';
const OFFLINE_URL = '/static/offline.html';

// Static assets to pre-cache on install
const STATIC_ASSETS = [
  '/static/offline.html',
  '/static/manifest.json',
  '/static/css/base.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
];

// Pages to cache after first visit (dynamic cache)
const CACHE_PAGES = [
  '/login',
  '/ci/dashboard',
  '/loan/dashboard',
  '/admin/dashboard',
  '/loan/submit',
  '/messages',
  '/notifications',
  '/ci/application',
  '/admin/application',
  '/loan/application',
  '/change_password',
  '/ci/tracking',
  '/manage_users',
];

// ── Install: pre-cache static assets + request persistent storage ──────────
self.addEventListener('install', event => {
  event.waitUntil(
    Promise.all([
      caches.open(CACHE_NAME)
        .then(cache => cache.addAll(STATIC_ASSETS).catch(() => {})),
      // Request persistent storage
      navigator.storage && navigator.storage.persist 
        ? navigator.storage.persist() 
        : Promise.resolve(false)
    ]).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ─────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip chrome-extension and non-http requests
  if (!url.protocol.startsWith('http')) return;

  // ── POST/PUT: try network, queue if offline ──────────────────────────────
  if (request.method === 'POST' || request.method === 'PUT') {
    event.respondWith(
      fetch(request.clone())
        .catch(async () => {
          await queueRequest(request.clone());
          // Return a response that tells the page the data was saved offline
          return new Response(
            `<script>
              sessionStorage.setItem('offlineSaved', '1');
              window.history.back();
            </script>`,
            {
              status: 200,
              headers: { 'Content-Type': 'text/html' }
            }
          );
        })
    );
    return;
  }

  // ── GET: network first, fallback to cache ────────────────────────────────
  event.respondWith(
    fetch(request, { credentials: 'include' })
      .then(response => {
        // Cache successful page responses including authenticated ones
        if (response.status === 200 && (
          request.mode === 'navigate' ||
          CACHE_PAGES.some(p => url.pathname.startsWith(p)) ||
          url.pathname.startsWith('/static/')
        )) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      })
      .catch(async () => {
        // Network failed - try exact cache match first
        const cached = await caches.match(request);
        if (cached) return cached;

        // Try without query string
        const urlWithoutQuery = new Request(url.origin + url.pathname);
        const cached2 = await caches.match(urlWithoutQuery);
        if (cached2) return cached2;

        // If navigating to login while offline, try to serve cached dashboard
        if (request.mode === 'navigate' && url.pathname === '/login') {
          const dashboards = ['/ci/dashboard', '/loan/dashboard', '/admin/dashboard'];
          for (const dash of dashboards) {
            const cachedDash = await caches.match(url.origin + dash);
            if (cachedDash) return cachedDash;
          }
        }

        // Last resort - offline page
        if (request.mode === 'navigate') return caches.match(OFFLINE_URL);
        return new Response('Offline', { status: 503 });
      })
  );
});

// ── Background Sync - Auto-upload when connection returns ───────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-pending' || event.tag === 'upload-checklists') {
    event.waitUntil(syncPendingRequests());
  }
});

// Register periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'auto-sync') {
    event.waitUntil(syncPendingRequests());
  }
});

// ── Queue a failed POST into IndexedDB ───────────────────────────────────────
async function queueRequest(request) {
  try {
    const body = await request.text();
    const db = await openDB();
    const tx = db.transaction('pending', 'readwrite');
    tx.objectStore('pending').add({
      url: request.url,
      method: request.method,
      headers: [...request.headers.entries()],
      body,
      timestamp: Date.now()
    });
  } catch (e) {
    console.error('Queue error:', e);
  }
}

// ── Replay all queued requests when back online ───────────────────────────────
async function syncPendingRequests() {
  const db = await openDB();
  const all = await getAll(db, 'pending');

  let synced = 0;
  for (const item of all) {
    try {
      const res = await fetch(item.url, {
        method: item.method,
        headers: new Headers(item.headers),
        body: item.body,
        credentials: 'include'
      });
      if (res.ok || res.status === 302 || res.redirected) {
        await deleteItem(db, 'pending', item.id);
        synced++;
      }
    } catch (e) {
      // Still offline, keep in queue
    }
  }

  // Notify all open tabs
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  clients.forEach(client => client.postMessage({
    type: 'SYNC_COMPLETE',
    count: synced
  }));
}

// ── IndexedDB helpers ─────────────────────────────────────────────────────────
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('ci-staff-offline', 2);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pending')) {
        db.createObjectStore('pending', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function getAll(db, storeName) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function deleteItem(db, storeName, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}
