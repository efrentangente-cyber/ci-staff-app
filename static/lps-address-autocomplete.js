/**
 * LPS / loan form: member_address suggestions from global addressDatabase (addresses.js).
 * - Strict AND: every query token appears somewhere in row (purok + barangay + mun + province).
 * - Fallback: token exactly equals a catalogue barangay name → show all rows under that barangay
 *   so every purok line is visible (rank rows where other tokens appear in `purok` first).
 * - Last resort lone token ≥5 chars: substring match inside `purok` field only (avoids province floods).
 */
(function () {
    'use strict';

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

    function collectMatches(tokens, db) {
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

        if (tokens.length === 1 && tokens[0].length >= 5) {
            var needle = tokens[0];
            var weak = [];
            for (i = 0; i < db.length; i++) {
                var pr = db[i].purok;
                var pl = typeof pr === 'string' ? pr.toLowerCase() : '';
                if (pl && pl.indexOf(needle) !== -1) {
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

        var input = document.getElementById(inputId);
        var list = document.getElementById(listId);
        if (!input || !list) {
            return;
        }
        if (input.readOnly || input.disabled) {
            return;
        }
        if (typeof addressDatabase === 'undefined' || !addressDatabase.length) {
            return;
        }

        input.addEventListener('input', function () {
            var raw = input.value;
            var trimmed = raw.trim();
            if (trimmed.length < 2) {
                list.style.display = 'none';
                return;
            }
            var tokens = tokenize(raw);
            if (tokens.length === 0) {
                list.style.display = 'none';
                return;
            }

            var out = collectMatches(tokens, addressDatabase);
            var scored = out.rows;
            var anchored = out.anchoredBrgyNorm;

            scored.sort(function (a, b) {
                return compareRows(a, b, tokens, anchored);
            });
            var matches = scored.slice(0, maxResults);

            if (matches.length === 0) {
                list.style.display = 'none';
                return;
            }

            list.innerHTML = '';
            matches.forEach(function (addr) {
                var fullAddress = addr.purok
                    ? addr.purok + ', ' + addr.barangay + ', ' + addr.municipality + ', ' + addr.province
                    : addr.barangay + ', ' + addr.municipality + ', ' + addr.province;

                var item = document.createElement('a');
                item.href = '#';
                item.className = 'list-group-item list-group-item-action';
                item.innerHTML =
                    '<div class="d-flex w-100 justify-content-between">' +
                    '<h6 class="mb-1">' +
                    (addr.purok || addr.barangay) +
                    '</h6>' +
                    '<small class="text-muted">' +
                    addr.municipality +
                    '</small></div>' +
                    '<small class="text-muted">' +
                    fullAddress +
                    '</small>';

                item.addEventListener('click', function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    input.value = fullAddress;
                    input.focus();
                    list.style.display = 'none';
                });
                item.addEventListener('mousedown', function (ev) {
                    ev.preventDefault();
                    input.value = fullAddress;
                });
                list.appendChild(item);
            });
            list.style.display = 'block';
        });

        document.addEventListener('click', function (e) {
            if (e.target !== input && !list.contains(e.target)) {
                setTimeout(function () {
                    list.style.display = 'none';
                }, 150);
            }
        });
    };
})();
