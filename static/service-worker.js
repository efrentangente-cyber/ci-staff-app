// DCCCO CI Staff App — caches assets/pages for resilient loading; workflows require network.
const CACHE_NAME = 'dccco-staff-v25';

const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/css/base.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap-icons/bootstrap-icons.css',
  '/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2',
  '/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff',
  '/static/ci-checklist-wizard.js',
  '/static/ci-checklist-wizard.css',
  '/static/excel-spreadsheet.js',
  '/static/excel-spreadsheet.css',
  '/static/signature-pad.js',
  '/static/ci-location-tracker.js',
  '/static/ci-doc-fullscreen-zoom.js',
  '/static/ci-doc-fullscreen-zoom.css',
];

const CACHE_PAGES = [
  '/login',
  '/ci/dashboard',
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

function isLoanDocumentMediaPath(pathname) {
  if (pathname.startsWith('/view_document/')) return true;
  return /^\/download\/\d+$/.test(pathname);
}

function isDocumentNavigation(request) {
  return request.mode === 'navigate' || request.destination === 'document';
}

const OFFLINE_NAV_FALLBACKS = [
  '/ci/dashboard',
  '/loan/dashboard',
  '/admin/dashboard',
  '/notifications',
  '/messages',
  '/change_password',
  '/login',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {})),
      navigator.storage && navigator.storage.persist ? navigator.storage.persist() : Promise.resolve(false)
    ]).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(async () => {
        try {
          if (
            self.registration &&
            self.registration.navigationPreload &&
            typeof self.registration.navigationPreload.enable === 'function'
          ) {
            await self.registration.navigationPreload.enable();
          }
        } catch {
          /* ignore — not supported or permission */
        }
      })
      .then(() => self.clients.claim())
  );
});

async function cachedNavigationFallback(request, url) {
  const origin = url.origin;
  const docNav = isDocumentNavigation(request);

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

  if (docNav) {
    const p = url.pathname;
    if (p.startsWith('/ci/review/') || p.startsWith('/ci/checklist/')) {
      const cache = await caches.open(CACHE_NAME);
      const keys = await cache.keys();
      for (let i = 0; i < keys.length; i++) {
        const req = keys[i];
        const ru = new URL(req.url);
        if (ru.origin === origin && ru.pathname === p) {
          const m = await cache.match(req);
          if (m && m.ok) return m;
        }
      }
    }
  }

  if (docNav && url.pathname === '/login') {
    const dashboards = ['/ci/dashboard', '/loan/dashboard', '/admin/dashboard'];
    for (let i = 0; i < dashboards.length; i++) {
      const c = await tryMatch(origin + dashboards[i]);
      if (c) return c;
    }
  }

  if (docNav) {
    for (let j = 0; j < OFFLINE_NAV_FALLBACKS.length; j++) {
      const c = await tryMatch(origin + OFFLINE_NAV_FALLBACKS[j]);
      if (c) return c;
    }
  }

  return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
}

async function findCachedByExactPath(origin, pathname) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const keys = await cache.keys();
    for (let i = 0; i < keys.length; i++) {
      const req = keys[i];
      let ru;
      try {
        ru = new URL(req.url);
      } catch {
        continue;
      }
      if (ru.origin !== origin || ru.pathname !== pathname) continue;
      const res = await cache.match(req);
      if (res && res.ok && res.status === 200) return res;
    }
  } catch {
    /* ignore */
  }
  return null;
}

async function putInCacheIfEligible(request, url, response) {
  if (!response || response.status !== 200 || !response.ok) return;
  const isGeneratedOrAddressCatalogue =
    url.pathname.includes('/static/generated/') ||
    url.pathname.endsWith('/addresses.js') ||
    url.pathname.endsWith('/ci-coverage-route-wizard.js');
  const path = url.pathname;
  const cacheByPrefix = CACHE_PAGES.some((p) => path.startsWith(p));
  const cacheDocMedia = isLoanDocumentMediaPath(path);
  const docNav = isDocumentNavigation(request);
  if (
    docNav ||
    path === '/' ||
    cacheByPrefix ||
    cacheDocMedia ||
    (path.startsWith('/static/') && !isGeneratedOrAddressCatalogue)
  ) {
    try {
      const clone = response.clone();
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, clone);
    } catch {
      /* quota / opaque — ignore */
    }
  }
}

const OFFLINE_HELP_HTML = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline</title><style>body{font-family:system-ui,sans-serif;max-width:36rem;margin:2rem auto;padding:0 1rem;line-height:1.45}</style></head><body><h1>You're offline</h1><p>This page isn’t cached on this device yet, or CI actions need an active internet connection.</p><p><strong>Reconnect</strong> then open the app again.</p></body></html>`;

function offlineShellResponse() {
  return new Response(OFFLINE_HELP_HTML, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }
  });
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (!url.protocol.startsWith('http')) return;

  const path = url.pathname;
  if (path.startsWith('/api/') || path.startsWith('/socket.io')) {
    return;
  }

  event.respondWith(
    (async () => {
      try {
        const docNav = isDocumentNavigation(request);
        const ciShell =
          docNav &&
          (path.startsWith('/ci/review/') || path.startsWith('/ci/checklist/'));

        let networkResponse = null;
        let networkFailed = false;

        const usePreload =
          docNav &&
          typeof event.preloadResponse !== 'undefined' &&
          event.preloadResponse != null;

        if (usePreload) {
          try {
            const pre = await event.preloadResponse.catch(() => null);
            if (pre && pre.ok) {
              networkResponse = pre;
            }
          } catch {
            /* ignore */
          }
        }

        if (!networkResponse) {
          try {
            networkResponse = await fetch(request, { credentials: 'include' });
          } catch {
            networkFailed = true;
            networkResponse = null;
          }
        }

        if (networkResponse && networkResponse.ok) {
          void putInCacheIfEligible(request, url, networkResponse).catch(() => {});
          return networkResponse;
        }

        if (networkFailed || !networkResponse) {
          if (docNav) {
            const exact = await findCachedByExactPath(url.origin, path);
            if (exact) return exact;

            let fromCache = await caches.match(request, { ignoreSearch: true }).catch(() => null);
            if (fromCache) return fromCache;
            const pathOnly = new Request(url.origin + path, { credentials: 'include' });
            fromCache = await caches.match(pathOnly, { ignoreSearch: true }).catch(() => null);
            if (fromCache) return fromCache;
          }

          if (isLoanDocumentMediaPath(path)) {
            let fromDoc = await caches
              .match(new Request(url.origin + path, { credentials: 'include' }), { ignoreSearch: true })
              .catch(() => null);
            if (fromDoc) return fromDoc;
          }
          if (path.startsWith('/static/')) {
            let st = await caches
              .match(new Request(url.origin + path, { credentials: 'include' }), { ignoreSearch: true })
              .catch(() => null);
            if (st) return st;
          }

          const fallback = await cachedNavigationFallback(request, url);
          if (fallback && (!ciShell || fallback.ok)) return fallback;
          return offlineShellResponse();
        }

        return networkResponse;
      } catch {
        try {
          const exact = await findCachedByExactPath(url.origin, url.pathname);
          if (exact) return exact;
          const fb = await cachedNavigationFallback(request, url);
          if (fb) return fb;
        } catch {
          /* ignore */
        }
        return offlineShellResponse();
      }
    })()
  );
});

self.addEventListener('sync', () => {});
self.addEventListener('periodicsync', () => {});
