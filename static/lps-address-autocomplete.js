/**
 * LPS / loan form: member_address suggestions from global addressDatabase (addresses.js).
 * Expects addressDatabase with barangay rows + purok rows (synthetic or overrides).
 */
(function () {
    'use strict';

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

    function compareRows(a, b, tokens) {
        var d = scoreRow(b, tokens) - scoreRow(a, tokens);
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

    window.initLpsAddressAutocomplete = function (opts) {
        var o = opts || {};
        var inputId = o.inputId || 'member_address';
        var listId = o.listId || 'address_suggestions';
        var maxResults = typeof o.maxResults === 'number' ? o.maxResults : 60;

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

            var scored = [];
            var i;
            for (i = 0; i < addressDatabase.length; i++) {
                var addr = addressDatabase[i];
                if (!allTokensInRow(addr, tokens)) {
                    continue;
                }
                scored.push(addr);
            }

            scored.sort(function (a, b) {
                return compareRows(a, b, tokens);
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
