// DCCCO CI Staff App - cache pages for offline (must register at /service-worker.js so scope is /)
const CACHE_NAME = 'dccco-staff-v15';
const OFFLINE_URL = '/static/offline.html';

// Static assets to pre-cache on install (Bootstrap Icons are self-hosted so fonts load with CSS — no CDN font delay).
const STATIC_ASSETS = [
  '/static/offline.html',
  '/static/manifest.json',
  '/static/css/base.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap-icons/bootstrap-icons.css',
  '/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2',
  '/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff',
];

// Pages to cache after first successful online visit — prefix match (do not use '/' alone).
const CACHE_PAGES = [
  '/login',
  '/ci/dashboard',
  '/ci/offline_saves',
  '/loan/dashboard',
  '/admin/dashboard',
  '/loan/submit',
  '/notifications',
  '/messages',
  '/ci/application',
  '/ci/review',
  '/ci/checklist',
  '/admin/application',
  '/loan/application',
  '/change_password',
  '/ci-tracking',
  '/manage_users',
];

/**
 * When a navigation is not in Cache Storage, serve the first available cached app page
 * so staff can keep working (dashboard, assignments, checklists opened while online).
 */
const OFFLINE_NAV_FALLBACKS = [
  '/ci/dashboard',
  '/loan/dashboard',
  '/admin/dashboard',
  '/notifications',
  '/messages',
  '/ci/offline_saves',
  '/change_password',
  '/login',
];

// ── Install: pre-cache static assets + request persistent storage ──────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {})),
      navigator.storage && navigator.storage.persist ? navigator.storage.persist() : Promise.resolve(false)
    ]).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/**
 * @param {Request} request
 * @param {URL} url
 */
async function cachedNavigationFallback(request, url) {
  const origin = url.origin;

  /** @param {Request|string} reqLike */
  const tryMatch = async (reqLike) => {
    let r = await caches.match(reqLike);
    if (r) return r;
    r = await caches.match(reqLike, { ignoreSearch: true });
    if (r) return r;
    if (typeof reqLike === 'string') {
      const r2 = await caches.match(new Request(reqLike, { credentials: 'include' }));
      if (r2) return r2;
      return caches.match(new Request(reqLike, { credentials: 'include' }), { ignoreSearch: true });
    }
    return null;
  };

  let cached = await tryMatch(request);
  if (cached) return cached;

  const pathOnlyReq = new Request(origin + url.pathname, { credentials: 'include' });
  cached = await tryMatch(pathOnlyReq);
  if (cached) return cached;

  if (request.mode === 'navigate' && url.pathname === '/login') {
    const dashboards = ['/ci/dashboard', '/loan/dashboard', '/admin/dashboard'];
    for (let i = 0; i < dashboards.length; i++) {
      const c = await tryMatch(origin + dashboards[i]);
      if (c) return c;
    }
  }

  if (request.mode === 'navigate') {
    for (let j = 0; j < OFFLINE_NAV_FALLBACKS.length; j++) {
      const c = await tryMatch(origin + OFFLINE_NAV_FALLBACKS[j]);
      if (c) return c;
    }
  }

  if (request.mode === 'navigate') {
    const off = await tryMatch(origin + OFFLINE_URL);
    if (off) return off;
  }
  return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
}

// ── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (!url.protocol.startsWith('http')) return;

  event.respondWith(
    fetch(request, { credentials: 'include' })
      .then((response) => {
        const isGeneratedOrAddressCatalogue =
          url.pathname.includes('/static/generated/') ||
          url.pathname.endsWith('/addresses.js') ||
          url.pathname.endsWith('/ci-coverage-route-wizard.js');

        const path = url.pathname;
        const cacheByPrefix = CACHE_PAGES.some((p) => path.startsWith(p));

        if (
          response.status === 200 &&
          (request.mode === 'navigate' ||
            path === '/' ||
            cacheByPrefix ||
            (path.startsWith('/static/') && !isGeneratedOrAddressCatalogue))
        ) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => cachedNavigationFallback(request, url))
  );
});

self.addEventListener('sync', () => {});
self.addEventListener('periodicsync', () => {});
