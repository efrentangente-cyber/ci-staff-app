/**
 * LPS / loan form: member_address suggestions from global addressDatabase (addresses.js).
 * - Strict AND: every query token appears somewhere in row (purok + barangay + mun + province).
 * - Comma segments: "Purok ..., Basay, Negros Oriental" — first segment anchors purok/barangay hint; later segments refine (typo-plural tolerant).
 * - Fallback: merged tokens (e.g. two-word barangay), barangay-only pool, loose multi-token, then purok/barangay substring.
 */
(function () {
    'use strict';

    /** PSGC list can load after scripts run; LPS autocomplete must read fresh rows each keystroke. */
    function resolveAddressCatalogueRows() {
        try {
            if (
                typeof window !== 'undefined' &&
                window.addressDatabase != null &&
                typeof window.addressDatabase.length === 'number'
            ) {
                return window.addressDatabase;
            }
        } catch (e0) {
            void e0;
        }
        try {
            if (typeof addressDatabase !== 'undefined' && addressDatabase != null) {
                return addressDatabase;
            }
        } catch (e1) {
            void e1;
        }
        return [];
    }

    var BRGY_CACHE = null;

    function normalizeSp(text) {
        return String(text || '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    function tokenize(raw) {
        return String(raw || '')
            .toLowerCase()
            .split(/[\s,]+/)
            .filter(function (t) {
                if (!t) {
                    return false;
                }
                if (t.length >= 2) {
                    return true;
                }
                return /^\d+$/.test(t);
            });
    }

    function rowHaystack(addr) {
        return [addr.purok, addr.barangay, addr.municipality, addr.province]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();
    }

    function allTokensInRow(addr, tokens) {
        var hay = rowHaystack(addr);
        return tokens.every(function (t) {
            return hay.indexOf(t) !== -1;
        });
    }

    function scoreRow(addr, tokens) {
        var p = (addr.purok || '').toLowerCase();
        var b = (addr.barangay || '').toLowerCase();
        var m = (addr.municipality || '').toLowerCase();
        var pr = (addr.province || '').toLowerCase();
        var s = 0;
        var tk;
        for (var i = 0; i < tokens.length; i++) {
            tk = tokens[i];
            if (p.indexOf(tk) !== -1) {
                s += 100;
            }
            if (b.indexOf(tk) !== -1) {
                s += 60;
            }
            if (m.indexOf(tk) !== -1) {
                s += 35;
            }
            if (pr.indexOf(tk) !== -1) {
                s += 25;
            }
        }
        var j;
        for (j = 0; j < tokens.length; j++) {
            tk = tokens[j];
            if (p.indexOf(tk) !== -1) {
                s += 40;
                break;
            }
        }
        for (j = 0; j < tokens.length; j++) {
            tk = tokens[j];
            if (b.indexOf(tk) === 0 || b.indexOf(' ' + tk) !== -1) {
                s += 20;
                break;
            }
        }
        if (addr.synthetic) {
            s -= 4;
        }
        return s;
    }

    /** Prefer matches on purok for tokens that aren't the anchored barangay name. */
    function anchorBoostScore(addr, tokens, anchoredBrgyNorm) {
        var s = scoreRow(addr, tokens);
        if (!anchoredBrgyNorm) {
            return s;
        }
        var p = (addr.purok || '').toLowerCase();
        var tk;
        for (var i = 0; i < tokens.length; i++) {
            tk = tokens[i];
            if (tk === anchoredBrgyNorm || !tk) {
                continue;
            }
            if (p.indexOf(tk) !== -1) {
                s += 450;
            }
        }
        return s;
    }

    function compareRows(a, b, tokens, anchoredBrgyNorm) {
        var d = anchorBoostScore(b, tokens, anchoredBrgyNorm) - anchorBoostScore(a, tokens, anchoredBrgyNorm);
        if (d !== 0) {
            return d;
        }
        var ap = a.purok || '';
        var bp = b.purok || '';
        if (ap !== bp) {
            return ap.localeCompare(bp, undefined, { sensitivity: 'base' });
        }
        return (a.barangay + a.municipality).localeCompare(b.barangay + b.municipality, undefined, {
            sensitivity: 'base',
        });
    }

    function distinctBrgyTriples(db) {
        var map = {};
        var i;
        for (i = 0; i < db.length; i++) {
            var a = db[i];
            var brgy = String(a.barangay || '').trim();
            if (!brgy) {
                continue;
            }
            var mun = String(a.municipality || '').trim();
            var prov = String(a.province || '').trim();
            var k = brgy + '\n' + mun + '\n' + prov;
            if (!map[k]) {
                map[k] = { barangay: brgy, municipality: mun, province: prov };
            }
        }
        var list = [];
        for (var key in map) {
            if (Object.prototype.hasOwnProperty.call(map, key)) {
                list.push(map[key]);
            }
        }
        return list;
    }

    function tripleEqualsRow(triple, addr) {
        return (
            String(addr.barangay || '').trim() === triple.barangay &&
            String(addr.municipality || '').trim() === triple.municipality &&
            String(addr.province || '').trim() === triple.province
        );
    }

    function commaSegments(raw) {
        return String(raw || '')
            .split(',')
            .map(function (s) {
                return normalizeSp(s);
            })
            .filter(Boolean);
    }

    function relaxedTokenInHaystack(hay, tok) {
        if (!tok) {
            return false;
        }
        if (hay.indexOf(tok) !== -1) {
            return true;
        }
        if (tok.length >= 5 && tok.slice(-1) === 's' && hay.indexOf(tok.slice(0, -1)) !== -1) {
            return true;
        }
        if (tok.length >= 5 && tok.slice(-1) !== 's' && hay.indexOf(tok + 's') !== -1) {
            return true;
        }
        return false;
    }

    function refinementSegmentMatches(addr, segText) {
        var hay = rowHaystack(addr);
        var phrase = normalizeSp(segText);
        if (phrase.length >= 2 && hay.indexOf(phrase) !== -1) {
            return true;
        }
        var toks = tokenize(segText);
        if (!toks.length) {
            return phrase.length >= 2 && hay.indexOf(phrase) !== -1;
        }
        var i;
        for (i = 0; i < toks.length; i++) {
            if (!relaxedTokenInHaystack(hay, toks[i])) {
                return false;
            }
        }
        return true;
    }

    function primarySegmentMatches(addr, segText) {
        var ptoks = tokenize(segText);
        if (!ptoks.length) {
            return false;
        }
        var pk = String(addr.purok || '').toLowerCase();
        var br = String(addr.barangay || '').toLowerCase();
        var fused = rowHaystack(addr);
        var i;
        for (i = 0; i < ptoks.length; i++) {
            var t = ptoks[i];
            if (pk && pk.indexOf(t) !== -1) {
                continue;
            }
            if (br && br.indexOf(t) !== -1) {
                continue;
            }
            if (relaxedTokenInHaystack(fused, t)) {
                continue;
            }
            if (t.length >= 3 && fused.indexOf(t) !== -1) {
                continue;
            }
            return false;
        }
        return true;
    }

    function commaSeparatedCollect(raw, db) {
        if (String(raw || '').indexOf(',') === -1) {
            return null;
        }
        var segs = commaSegments(raw);
        if (segs.length < 2) {
            return null;
        }
        var pool = [];
        var i;
        for (i = 0; i < db.length; i++) {
            if (!primarySegmentMatches(db[i], segs[0])) {
                continue;
            }
            var k;
            var ok = true;
            for (k = 1; k < segs.length; k++) {
                if (!refinementSegmentMatches(db[i], segs[k])) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                pool.push(db[i]);
            }
        }
        return pool.length ? pool : null;
    }

    function looseMultiTokenCollect(tokens, db) {
        if (tokens.length < 2) {
            return null;
        }
        var need = Math.max(2, Math.ceil(tokens.length * 0.51));
        var pool = [];
        var i;
        for (i = 0; i < db.length; i++) {
            var hay = rowHaystack(db[i]);
            var t0 = tokens[0];
            var pk = String(db[i].purok || '').toLowerCase();
            var anchored =
                (pk && pk.indexOf(t0) !== -1) ||
                relaxedTokenInHaystack(hay, t0) ||
                (t0.length >= 3 && hay.indexOf(t0) !== -1);
            if (!anchored) {
                continue;
            }
            var hit = 0;
            var j;
            for (j = 0; j < tokens.length; j++) {
                if (relaxedTokenInHaystack(hay, tokens[j]) || hay.indexOf(tokens[j]) !== -1) {
                    hit += 1;
                }
            }
            if (hit >= need) {
                pool.push(db[i]);
            }
        }
        return pool.length ? pool : null;
    }

    function collectMatches(raw, tokens, db) {
        var strict = [];
        var i;
        for (i = 0; i < db.length; i++) {
            if (allTokensInRow(db[i], tokens)) {
                strict.push(db[i]);
            }
        }
        if (strict.length) {
            return { rows: strict, anchoredBrgyNorm: null };
        }

        /* e.g. "caranoche santa catalina" — treat "santa catalina" as one token for row matching */
        if (tokens.length >= 2) {
            for (var mi = 0; mi < tokens.length - 1; mi++) {
                var mergedTok = tokens[mi] + ' ' + tokens[mi + 1];
                var alt = tokens.slice();
                alt.splice(mi, 2, mergedTok);
                var relaxed = [];
                for (var rj = 0; rj < db.length; rj++) {
                    if (allTokensInRow(db[rj], alt)) {
                        relaxed.push(db[rj]);
                    }
                }
                if (relaxed.length) {
                    return { rows: relaxed, anchoredBrgyNorm: normalizeSp(mergedTok) };
                }
            }
        }

        var commaPool = commaSeparatedCollect(raw, db);
        if (commaPool && commaPool.length) {
            return { rows: commaPool, anchoredBrgyNorm: null };
        }

        if (!BRGY_CACHE || BRGY_CACHE._dbLen !== db.length) {
            BRGY_CACHE = { triples: distinctBrgyTriples(db), _dbLen: db.length };
        }
        var triples = BRGY_CACHE.triples;
        var matchedTriples = [];
        for (i = 0; i < triples.length; i++) {
            var tr = triples[i];
            var bn = normalizeSp(tr.barangay);
            var matched = false;
            var j;
            for (j = 0; j < tokens.length; j++) {
                if (tokens[j] === bn) {
                    matched = true;
                    break;
                }
            }
            if (matched) {
                matchedTriples.push(tr);
            }
        }

        if (matchedTriples.length === 1) {
            var pool = [];
            var trOnly = matchedTriples[0];
            for (i = 0; i < db.length; i++) {
                if (tripleEqualsRow(trOnly, db[i])) {
                    pool.push(db[i]);
                }
            }
            if (pool.length) {
                return {
                    rows: pool,
                    anchoredBrgyNorm: normalizeSp(trOnly.barangay),
                };
            }
        }

        var looseMt = looseMultiTokenCollect(tokens, db);
        if (looseMt && looseMt.length) {
            return { rows: looseMt, anchoredBrgyNorm: null };
        }

        if (tokens.length === 1 && tokens[0].length >= 3) {
            var needle = tokens[0];
            var weak = [];
            for (i = 0; i < db.length; i++) {
                var pr = db[i].purok;
                var pl = typeof pr === 'string' ? pr.toLowerCase() : '';
                var brg = typeof db[i].barangay === 'string' ? db[i].barangay.toLowerCase() : '';
                if ((pl && pl.indexOf(needle) !== -1) || (brg && brg.indexOf(needle) !== -1)) {
                    weak.push(db[i]);
                }
            }
            if (weak.length) {
                return { rows: weak, anchoredBrgyNorm: null };
            }
        }

        return { rows: [], anchoredBrgyNorm: null };
    }

    window.initLpsAddressAutocomplete = function (opts) {
        var o = opts || {};
        var inputId = o.inputId || 'member_address';
        var listId = o.listId || 'address_suggestions';
        var maxResults = typeof o.maxResults === 'number' ? o.maxResults : 180;
        var pollMs = typeof o.pollMs === 'number' ? o.pollMs : 100;
        var maxAttempts = typeof o.maxAttempts === 'number' ? o.maxAttempts : 100;
        var debounceMs = typeof o.debounceMs === 'number' ? o.debounceMs : 72;

        function attachAutocomplete(forceAttach) {
            var input = document.getElementById(inputId);
            var list = document.getElementById(listId);
            if (!input || !list) {
                return false;
            }
            if (input.readOnly || input.disabled) {
                return true;
            }
            if (input.dataset.lpsAddressAcBound === '1') {
                return true;
            }
            var catalogueRows = resolveAddressCatalogueRows();
            if (!catalogueRows.length && !forceAttach) {
                return false;
            }

            input.dataset.lpsAddressAcBound = '1';
            list.setAttribute('role', 'listbox');
            list.style.zIndex = '1090';
            input.setAttribute('aria-autocomplete', 'list');
            input.setAttribute('aria-controls', listId);

            var debounceTimer = null;

            /** Label + input + list share one .position-relative wrapper — clicks there must not close the list. */
            var wrap = input.closest('.position-relative');

            function hideList() {
                list.style.display = 'none';
                list.innerHTML = '';
                input.setAttribute('aria-expanded', 'false');
            }

            function escapeHtml(str) {
                return String(str)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            }

            function flushSuggestionsFromCatalogue() {
                window.requestAnimationFrame(function () {
                    if (debounceTimer) {
                        clearTimeout(debounceTimer);
                        debounceTimer = null;
                    }
                    updateAddressSuggestionList();
                });
            }

            function updateAddressSuggestionList() {
                var raw = input.value;
                var trimmed = raw.trim();
                if (trimmed.length < 2) {
                    hideList();
                    return;
                }
                var tokens = tokenize(raw);
                if (tokens.length === 0) {
                    hideList();
                    return;
                }

                var dbLive = resolveAddressCatalogueRows();
                if (!dbLive.length) {
                    list.innerHTML = '';
                    var note = document.createElement('button');
                    note.type = 'button';
                    note.disabled = true;
                    note.className = 'list-group-item list-group-item-warning text-start small';
                    note.textContent =
                        'Address list not loaded. Hard refresh (Ctrl+Shift+R). Ask admin to verify static/generated/address_psgc_negros.generated.js is deployed.';
                    list.appendChild(note);
                    list.style.display = 'block';
                    input.setAttribute('aria-expanded', 'true');
                    return;
                }

                var out = collectMatches(raw, tokens, dbLive);
                var scored = out.rows;
                var anchored = out.anchoredBrgyNorm;

                scored.sort(function (a, b) {
                    return compareRows(a, b, tokens, anchored);
                });
                var matches = scored.slice(0, maxResults);

                if (matches.length === 0) {
                    hideList();
                    return;
                }

                list.innerHTML = '';
                matches.forEach(function (addr) {
                    var fullAddress = addr.purok
                        ? addr.purok + ', ' + addr.barangay + ', ' + addr.municipality + ', ' + addr.province
                        : addr.barangay + ', ' + addr.municipality + ', ' + addr.province;

                    var item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'list-group-item list-group-item-action text-start py-2';
                    item.setAttribute('role', 'option');
                    var pu = escapeHtml(addr.purok ? String(addr.purok) : '—');
                    var brgy = escapeHtml(String(addr.barangay || ''));
                    var mun = escapeHtml(String(addr.municipality || ''));
                    var prov = escapeHtml(String(addr.province || ''));
                    item.innerHTML =
                        '<div class="fw-semibold small">' +
                        pu +
                        '</div>' +
                        '<div class="text-muted small mt-1">' +
                        '<span>' +
                        brgy +
                        '</span>' +
                        ' · <span>' +
                        mun +
                        '</span>' +
                        ' · <span>' +
                        prov +
                        '</span></div>';

                    item.addEventListener('click', function () {
                        input.value = fullAddress;
                        input.focus();
                        hideList();
                    });
                    item.addEventListener('mousedown', function (ev) {
                        ev.preventDefault();
                        input.value = fullAddress;
                    });
                    list.appendChild(item);
                });
                list.style.display = 'block';
                input.setAttribute('aria-expanded', 'true');
            }

            input.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function () {
                    debounceTimer = null;
                    updateAddressSuggestionList();
                }, debounceMs);
            });

            input.addEventListener('focus', function () {
                clearTimeout(debounceTimer);
                if (input.value.trim().length >= 2) {
                    updateAddressSuggestionList();
                }
            });

            input.addEventListener('keydown', function (ev) {
                if (ev.key === 'Escape') {
                    hideList();
                }
            });

            window.addEventListener('dcccoAddressCatalogueReady', flushSuggestionsFromCatalogue);

            document.addEventListener('click', function (e) {
                var tgt = e.target;
                var insideComposite = wrap && tgt && wrap.contains(tgt);
                if (insideComposite) {
                    return;
                }
                if (tgt === input || list.contains(tgt)) {
                    return;
                }
                setTimeout(function () {
                    hideList();
                }, 120);
            });

            return true;
        }

        var attempts = 0;
        function schedule() {
            if (attachAutocomplete(false)) {
                return;
            }
            attempts += 1;
            if (attempts >= maxAttempts) {
                if (!attachAutocomplete(true)) {
                    console.warn(
                        'LPS address autocomplete: #member_address / #address_suggestions missing; autocomplete not bound.'
                    );
                }
                return;
            }
            setTimeout(schedule, pollMs);
        }
        schedule();
    };
})();
