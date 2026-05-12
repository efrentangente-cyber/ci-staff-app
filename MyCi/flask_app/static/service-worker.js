// DCCCO CI Staff App - Service Worker v14 — bypass SW for heavy multipart POSTs (faster WebView submit)
const CACHE_NAME = 'dccco-staff-v14';
const OFFLINE_URL = '/static/offline.html';

// Static assets to pre-cache on install
const STATIC_ASSETS = [
  '/static/offline.html',
  '/static/manifest.json',
  '/static/datatable.css',
  '/static/datatable.js',
  '/static/indexeddb-manager.js',
  '/static/offline-sync.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
];

// Pages to cache after first visit (dynamic cache)
const CACHE_PAGES = [
  '/ci/dashboard',
  '/loan/dashboard',
  '/admin/dashboard',
  '/loan/submit',
  '/messages',
  '/notifications',
  '/ci/offline_shell',
  '/change_password',
  '/ci/tracking',
  '/manage_users',
];

/**
 * Never store main-document navigations for per-app routes or login — a 200 can be a login
 * HTML body, which then poisons the cache for the interview URL.
 */
function shouldAvoidCachingNavigation(url) {
  const p = url.pathname || '';
  return (
    p.startsWith('/ci/application') ||
    p.startsWith('/ci/checklist') ||
    p.startsWith('/admin/application') ||
    p.startsWith('/loan/application') ||
    p === '/login' ||
    p.startsWith('/login?')
  );
}

/** Successful GET responses for these paths are cached (same UI online vs disconnected). */
function shouldCacheSuccessfulGet(url) {
  const path = url.pathname || '';
  if (path.startsWith('/static/')) return true;
  if (path.startsWith('/download')) return true;
  return CACHE_PAGES.some((p) => path.startsWith(p));
}

// ── Install: pre-cache static assets + request persistent storage ─────────
self.addEventListener('install', event => {
  event.waitUntil(
    Promise.all([
      caches.open(CACHE_NAME)
        .then(cache => cache.addAll(STATIC_ASSETS).catch(() => {})),
      // Request persistent storage (unlimited)
      navigator.storage && navigator.storage.persist ? 
        navigator.storage.persist().then(granted => {
          console.log('✅ Persistent storage:', granted ? 'GRANTED' : 'DENIED');
        }) : Promise.resolve()
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
    const p = url.pathname || '';
    // Large multipart uploads: let the browser handle the request directly. Cloning the body in
    // the SW duplicates memory and noticeably slows Android WebView submits.
    const bypassSwForMultipart =
      p === '/loan/submit' ||
      (p.startsWith('/ci/application/') && p !== '/ci/application') ||
      p === '/api/ci/complete_interview';
    if (bypassSwForMultipart) {
      return;
    }
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
        const isNavigate = request.mode === 'navigate';
        const mayCacheNavigate = isNavigate && !shouldAvoidCachingNavigation(url);
        if (response.status === 200 && (mayCacheNavigate || (!isNavigate && shouldCacheSuccessfulGet(url)))) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      })
      .catch(async () => {
        const path = url.pathname || '';
        const isNavigate = request.mode === 'navigate';
        const skipStaleAppShell =
          isNavigate &&
          (path.startsWith('/ci/application') ||
            path.startsWith('/ci/checklist') ||
            path.startsWith('/admin/application') ||
            path.startsWith('/loan/application'));

        if (!skipStaleAppShell) {
          const cached = await caches.match(request);
          if (cached) return cached;
          const urlWithoutQuery = new Request(url.origin + url.pathname);
          const cached2 = await caches.match(urlWithoutQuery);
          if (cached2) return cached2;
        }

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

// ── Background Sync ──────────────────────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-pending') {
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
// Use a dedicated DB so upgrades here never conflict with indexeddb-manager.js
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('sw-pending-queue', 1);
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
