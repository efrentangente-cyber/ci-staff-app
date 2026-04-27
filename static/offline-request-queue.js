/**
 * Offline outbox: same-origin mutating fetch() calls are queued when offline
 * or on network failure, then replayed when connectivity returns.
 * Requires authenticated session (body.authenticated).
 */
(function () {
  'use strict';
  if (!document.body || !document.body.classList.contains('authenticated')) {
    return;
  }

  var DB_NAME = 'dccco-offline-outbox';
  var DB_VER = 1;
  var STORE = 'requests';

  function getCSRFToken() {
    if (typeof window.getCSRFToken === 'function') {
      return window.getCSRFToken();
    }
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  }

  var nativeFetch = window.fetch.bind(window);
  var flushing = false;

  function sameOriginHref(href) {
    try {
      var u = new URL(href, location.origin);
      return u.origin === location.origin;
    } catch (e) {
      return false;
    }
  }

  function shouldSkip(urlStr, method) {
    var u = urlStr.toLowerCase();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
      return true;
    }
    if (u.indexOf('/socket.io') !== -1) return true;
    if (u.indexOf('session_heartbeat') !== -1) return true;
    return false;
  }

  function sanitizeHeaders(h) {
    var out = {};
    var forbidden = { 'content-length': 1, cookie: 1, host: 1, connection: 1 };
    if (!h) return out;
    if (typeof Headers !== 'undefined' && h instanceof Headers) {
      h.forEach(function (v, k) {
        if (!forbidden[k.toLowerCase()]) out[k] = v;
      });
    } else if (typeof h === 'object') {
      Object.keys(h).forEach(function (k) {
        if (!forbidden[k.toLowerCase()]) out[k] = h[k];
      });
    }
    return out;
  }

  function openDb() {
    return new Promise(function (resolve, reject) {
      var r = indexedDB.open(DB_NAME, DB_VER);
      r.onerror = function () { reject(r.error); };
      r.onsuccess = function () { resolve(r.result); };
      r.onupgradeneeded = function (e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  function dbAdd(record) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).add(record);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function dbGetAll() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readonly');
        var q = tx.objectStore(STORE).getAll();
        q.onsuccess = function () { resolve(q.result || []); };
        q.onerror = function () { reject(q.error); };
      });
    });
  }

  function dbDelete(id) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(id);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function emitCount() {
    dbGetAll().then(function (rows) {
      window.__dcccoPendingCount = rows.length;
      window.dispatchEvent(new CustomEvent('dccco-outbox-changed', {
        detail: { count: rows.length },
      }));
    }).catch(function () {});
  }

  function captureBody(body, headersFlat) {
    if (body == null || body === undefined) {
      return Promise.resolve({ kind: 'empty', payload: null });
    }
    if (typeof body === 'string') {
      return Promise.resolve({ kind: 'text', payload: body, contentType: headersFlat['Content-Type'] || headersFlat['content-type'] });
    }
    if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) {
      return Promise.resolve({
        kind: 'text',
        payload: body.toString(),
        contentType: 'application/x-www-form-urlencoded;charset=UTF-8',
      });
    }
    if (typeof FormData !== 'undefined' && body instanceof FormData) {
      var entries = [];
      var it = body.entries();
      function nextEntry() {
        var step = it.next();
        if (step.done) {
          return Promise.resolve({ kind: 'formdata', payload: entries });
        }
        var pair = step.value;
        var k = pair[0];
        var v = pair[1];
        if (typeof File !== 'undefined' && v instanceof File) {
          return v.arrayBuffer().then(function (buf) {
            entries.push({
              key: k, file: true, name: v.name, type: v.type || 'application/octet-stream', buffer: buf,
            });
            return nextEntry();
          });
        }
        entries.push({ key: k, file: false, value: String(v) });
        return nextEntry();
      }
      return nextEntry();
    }
    if (typeof Blob !== 'undefined' && body instanceof Blob) {
      return body.arrayBuffer().then(function (buf) {
        return {
          kind: 'buffer',
          payload: buf,
          contentType: headersFlat['Content-Type'] || headersFlat['content-type'] || 'application/octet-stream',
        };
      });
    }
    return Promise.resolve({ kind: 'text', payload: String(body) });
  }

  function rebuildBody(captured) {
    if (!captured || captured.kind === 'empty') return undefined;
    if (captured.kind === 'text') return captured.payload;
    if (captured.kind === 'buffer') return captured.payload;
    if (captured.kind === 'formdata') {
      var fd = new FormData();
      captured.payload.forEach(function (e) {
        if (e.file) {
          var blob = new Blob([e.buffer], { type: e.type });
          if (typeof File !== 'undefined') {
            fd.append(e.key, new File([blob], e.name, { type: e.type }));
          } else {
            fd.append(e.key, blob, e.name);
          }
        } else {
          fd.append(e.key, e.value);
        }
      });
      return fd;
    }
    return undefined;
  }

  function syntheticQueuedResponse() {
    return new Response(
      JSON.stringify({
        success: true,
        offline_queued: true,
        pending: true,
        message: 'Saved on this device. It will be sent when you are back online.',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json', 'X-Offline-Queued': '1' } }
    );
  }

  function enqueue(urlFull, method, init) {
    var headersFlat = sanitizeHeaders(init.headers);
    return captureBody(init.body, headersFlat).then(function (bodyCaptured) {
      return dbAdd({
        url: urlFull,
        method: method,
        headers: headersFlat,
        bodyCaptured: bodyCaptured,
        createdAt: Date.now(),
      });
    }).then(function () {
      emitCount();
    });
  }

  function flushOutbox() {
    if (!navigator.onLine || flushing) return Promise.resolve();
    flushing = true;
    return dbGetAll().then(function (rows) {
      if (!rows.length) return Promise.resolve();
      return rows.reduce(function (chain, row) {
        return chain.then(function () {
          var headers = new Headers(row.headers);
          var token = getCSRFToken();
          if (token) headers.set('X-CSRFToken', token);
          headers.set('X-Requested-With', 'XMLHttpRequest');
          var body = rebuildBody(row.bodyCaptured);
          if (row.bodyCaptured && row.bodyCaptured.kind === 'text' && row.bodyCaptured.contentType) {
            headers.set('Content-Type', row.bodyCaptured.contentType);
          }
          if (row.bodyCaptured && row.bodyCaptured.kind === 'formdata') {
            headers.delete('Content-Type');
          }
          var init = { method: row.method, headers: headers, credentials: 'include' };
          if (body !== undefined) init.body = body;
          return nativeFetch(row.url, init).then(function (res) {
            if (res.ok || res.status === 302 || res.status === 303 || res.status === 307 || res.status === 308) {
              return dbDelete(row.id);
            }
            if (res.status === 401 || res.status === 403) {
              throw new Error('auth');
            }
          });
        });
      }, Promise.resolve());
    }).catch(function () {
      /* keep queue on error */
    }).then(function () {
      flushing = false;
      emitCount();
    });
  }

  window.fetch = function (input, init) {
    init = init || {};
    if (typeof Request !== 'undefined' && input instanceof Request) {
      return nativeFetch(input, init);
    }
    var urlStr = typeof input === 'string' ? input : String(input);
    var urlFull = new URL(urlStr, location.origin).href;
    var method = (init.method || 'GET').toUpperCase();

    if (!sameOriginHref(urlFull) || shouldSkip(urlFull, method)) {
      return nativeFetch(input, init);
    }

    if (!navigator.onLine && ['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1) {
      return enqueue(urlFull, method, init).then(function () {
        return syntheticQueuedResponse();
      });
    }

    return nativeFetch(input, init).catch(function (err) {
      if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1) {
        return enqueue(urlFull, method, init).then(function () {
          return syntheticQueuedResponse();
        });
      }
      throw err;
    });
  };

  window.addEventListener('online', function () {
    flushOutbox();
  });
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && navigator.onLine) flushOutbox();
  });
  setInterval(function () {
    if (navigator.onLine) flushOutbox();
  }, 45000);

  window.DCCCOOutbox = {
    flush: flushOutbox,
    getPendingCount: function () {
      return dbGetAll().then(function (r) { return r.length; });
    },
  };

  document.addEventListener('DOMContentLoaded', function () {
    emitCount();
    if (navigator.onLine) flushOutbox();
  });

  // Full-page HTML form POSTs bypass fetch(); queue them the same way when offline.
  document.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (!form || form.tagName !== 'FORM') return;
    if (form.hasAttribute('data-skip-offline-queue')) return;
    var method = (form.getAttribute('method') || 'GET').toUpperCase();
    if (method !== 'POST' && method !== 'PUT') return;
    if (navigator.onLine) return;

    var action = form.action || window.location.href;
    if (!sameOriginHref(action)) return;

    ev.preventDefault();
    var fd = new FormData(form);
    fetch(action, { method: method, body: fd, credentials: 'include' })
      .then(function (res) { return res.json().catch(function () { return {}; }); })
      .then(function (j) {
        if (j && j.offline_queued) {
          if (window.syncManager && typeof window.syncManager.showToast === 'function') {
            window.syncManager.showToast('Offline: request saved. It will send when you reconnect.', 'warning');
          } else {
            window.alert('You are offline. This request was saved on your device and will be sent when you are back online.');
          }
        }
      })
      .catch(function () {
        window.alert('Could not save this request offline. Try again when you have a connection.');
      });
  }, true);

})();
