// DCCCO CI Staff App - Service Worker v7 - GET cache + offline shell (mutations queued in main thread)
const CACHE_NAME = 'dccco-staff-v7';
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

  // Mutating requests: handled by offline-request-queue.js (fetch wrapper) in the page.
  // Do not intercept POST/PUT here — breaks JSON, multipart, and CSRF replay.

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

// Background sync tags may still be registered from the page; no SW-side queue.
self.addEventListener('sync', () => {});

self.addEventListener('periodicsync', () => {});
