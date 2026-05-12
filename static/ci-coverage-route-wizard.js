/**
 * Manage Users — pinpoint coverage routes: municipality search → barangay from/to → POST create.
 * Options: opts.useCoverageCatalogApi + municipalities/barangays URLs (server parses PSGC JS), or
 * static/addresses.js (findCoverageMunicipalitiesMatching, listCoverageBarangaysInMunicipality).
 */
(function () {
    'use strict';

    function el(id) {
        return document.getElementById(id);
    }

    function fillSelect(sel, labels) {
        if (!sel) {
            return;
        }
        sel.innerHTML = '';
        var ph = document.createElement('option');
        ph.value = '';
        ph.textContent = labels.length ? 'Select…' : '—';
        sel.appendChild(ph);
        labels.forEach(function (t) {
            var o = document.createElement('option');
            o.value = t;
            o.textContent = t;
            sel.appendChild(o);
        });
        sel.disabled = labels.length === 0;
    }

    /** Dedupe + stable sort for barangay lists from API / cache. */
    function normalizeBarangayLabels(labels) {
        var seen = Object.create(null);
        var out = [];
        (labels || []).forEach(function (t) {
            var s = String(t || '').trim();
            if (!s) {
                return;
            }
            var k = s.toLowerCase();
            if (seen[k]) {
                return;
            }
            seen[k] = true;
            out.push(s);
        });
        out.sort(function (a, b) {
            return a.localeCompare(b, undefined, { sensitivity: 'base' });
        });
        return out;
    }

    function mirrorToOptions(fromSel, toSel) {
        if (!fromSel || !toSel || fromSel.options.length <= 1) {
            return;
        }
        var vTo = toSel.value;
        toSel.innerHTML = fromSel.innerHTML;
        if (toSel.options[0]) {
            toSel.options[0].textContent = fromSel.options[0].textContent;
        }
        var kept = Array.prototype.some.call(toSel.options, function (o) {
            return o.value === vTo;
        });
        if (kept) {
            toSel.value = vTo;
        }
    }

    /** From/to barangays + municipality disambiguation hints + extras. */
    function municipalityKeywordHint(mun) {
        return String(mun || '')
            .replace(/^City\s+of\s+/i, '')
            .trim()
            .toLowerCase();
    }

    function buildKeywordsDecoded(fromD, toD, extraCsv) {
        var kws = [];
        function add(s) {
            var t = String(s || '').trim().toLowerCase();
            if (!t || kws.indexOf(t) >= 0) {
                return;
            }
            kws.push(t);
        }
        if (fromD && fromD.barangay) {
            add(fromD.barangay);
            add(municipalityKeywordHint(fromD.municipality));
        }
        if (toD && toD.barangay) {
            add(toD.barangay);
            add(municipalityKeywordHint(toD.municipality));
        }
        (extraCsv || '').split(',').forEach(function (x) {
            add(x.trim());
        });
        return kws;
    }

    var DEFAULT_BRGY_HINT =
        'Lists update after each Search. From and To must be two different barangays.';

    function encodeCovOpt(mun, prov, brgy) {
        return 'cov\t' + mun + '\t' + prov + '\t' + brgy;
    }

    function decodeCovOpt(v) {
        var raw = String(v || '');
        if (raw.indexOf('cov\t') !== 0) {
            return null;
        }
        var parts = raw.slice(4).split('\t');
        if (parts.length !== 3) {
            return null;
        }
        return {
            municipality: parts[0],
            province: parts[1],
            barangay: parts[2],
        };
    }

    window.initCiCoverageRouteWizard = function (opts) {
        var wrap = opts && opts.rootId ? el(opts.rootId) : el('ciCoverageRouteWizard');
        if (!wrap) {
            return;
        }
        if (wrap.getAttribute('data-ci-wizard-bound') === '1') {
            return;
        }
        wrap.setAttribute('data-ci-wizard-bound', '1');

        var createUrl =
            opts && opts.createUrl
                ? opts.createUrl
                : wrap.getAttribute('data-create-url') || '';
        var csrfFn = opts && opts.getCsrf ? opts.getCsrf : function () {
            return '';
        };
        var apiHeadersFn = opts && opts.manageUsersApiHeaders ? opts.manageUsersApiHeaders : null;
        var useCatalogueApi =
            !!(opts &&
                opts.useCoverageCatalogApi &&
                opts.coverageMunicipalitiesUrl &&
                opts.coverageBarangaysUrl);
        var coverageMunicipalitiesUrl =
            useCatalogueApi ? String(opts.coverageMunicipalitiesUrl) : '';
        var coverageBarangaysUrl = useCatalogueApi ? String(opts.coverageBarangaysUrl) : '';
        var coverageCorridorBarangaysUrl =
            opts && opts.coverageCorridorBarangaysUrl
                ? String(opts.coverageCorridorBarangaysUrl)
                : '';

        function catalogueFetchHeaders() {
            var headers = {
                Accept: 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            };
            if (apiHeadersFn) {
                var h = apiHeadersFn();
                Object.assign(headers, h);
            }
            return headers;
        }

        /** Network JSON for catalogue endpoints; survives HTML error pages / timeouts without hanging UI. */
        function fetchCatalogueJson(url, timeoutMs) {
            var ms = timeoutMs || 120000;
            var ctrl = new AbortController();
            var timer = setTimeout(function () {
                ctrl.abort();
            }, ms);
            return fetch(url, {
                credentials: 'same-origin',
                headers: catalogueFetchHeaders(),
                signal: ctrl.signal,
            })
                .finally(function () {
                    clearTimeout(timer);
                })
                .then(function (r) {
                    return r.text().then(function (t) {
                        var parsed = null;
                        var parseOk = false;
                        try {
                            if (t != null && t.length > 0) {
                                parsed = JSON.parse(t);
                                parseOk = true;
                            }
                        } catch (e1) {
                            parseOk = false;
                        }
                        return {
                            okHttp: r.ok,
                            status: r.status,
                            data: parsed,
                            parseOk: parseOk,
                        };
                    });
                });
        }

        var placeIn = el('coveragePlaceSearch');
        var loadBtn = el('coverageLoadBrgysBtn');
        var munRow = el('coverageMunicipalityRow');
        var munSel = el('coverageMunicipalitySelect');
        var pickRow = el('coverageBrgyPickers');
        var msgEl = el('coverageMatchedAreaMsg');
        var fromSel = el('coverageBrgyFrom');
        var toSel = el('coverageBrgyTo');
        var preview = el('coverageRoutePreview');
        var kwExtra = el('coverageExtraKeywords');
        var saveBtn = el('createRouteSubmitBtn');
        var corridorPresetSel = el('coverageCorridorPreset');
        var brgyHintEl = el('coverageBrgyHint');

        var catalogueLoadingStack = [];

        function applyCatalogueLoadingUi() {
            if (!loadBtn) {
                return;
            }
            if (catalogueLoadingStack.length) {
                if (!loadBtn.dataset.origHtml) {
                    loadBtn.dataset.origHtml = loadBtn.innerHTML;
                }
                loadBtn.disabled = true;
                loadBtn.setAttribute('aria-busy', 'true');
                var top = catalogueLoadingStack[catalogueLoadingStack.length - 1];
                var lab =
                    top === 'barangays'
                        ? 'Loading barangays…'
                        : top === 'search'
                          ? 'Searching…'
                          : 'Please wait…';
                loadBtn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' +
                    lab;
                if (pickRow) {
                    if (top === 'barangays') {
                        pickRow.setAttribute('aria-busy', 'true');
                    } else {
                        pickRow.removeAttribute('aria-busy');
                    }
                }
            } else {
                loadBtn.disabled = false;
                loadBtn.removeAttribute('aria-busy');
                if (loadBtn.dataset.origHtml) {
                    loadBtn.innerHTML = loadBtn.dataset.origHtml;
                }
                if (pickRow) {
                    pickRow.removeAttribute('aria-busy');
                }
            }
        }

        function beginCatalogueLoading(kind) {
            catalogueLoadingStack.push(kind || 'wait');
            applyCatalogueLoadingUi();
        }

        function endCatalogueLoading() {
            catalogueLoadingStack.pop();
            applyCatalogueLoadingUi();
        }

        function resetCatalogueLoading() {
            catalogueLoadingStack.length = 0;
            applyCatalogueLoadingUi();
        }

        var state = {
            municipality: '',
            province: '',
            labels: [],
            multi: [],
            corridorPresetKey: '',
            corridorPresetDisplay: '',
        };
        var municipalitiesCache = Object.create(null);
        var barangaysCache = Object.create(null);

        function fillSelectCorridor(sel, items) {
            if (!sel) {
                return;
            }
            sel.innerHTML = '';
            var ph = document.createElement('option');
            ph.value = '';
            ph.textContent = items && items.length ? 'Select…' : '—';
            sel.appendChild(ph);
            var seenVal = Object.create(null);
            (items || []).forEach(function (it) {
                var o = document.createElement('option');
                var v = encodeCovOpt(it.municipality, it.province, it.barangay);
                if (seenVal[v]) {
                    return;
                }
                seenVal[v] = true;
                o.value = v;
                o.textContent =
                    it.label || it.barangay + ' — ' + it.municipality + ', ' + it.province;
                sel.appendChild(o);
            });
            sel.disabled = !items || items.length === 0;
        }

        function decodeBarangayChoice(v) {
            var raw = String(v || '').trim();
            if (!raw) {
                return null;
            }
            var d = decodeCovOpt(raw);
            if (d) {
                return d;
            }
            if (state.municipality) {
                return {
                    municipality: state.municipality,
                    province: state.province || '',
                    barangay: raw,
                };
            }
            return {
                municipality: '',
                province: '',
                barangay: raw,
            };
        }

        function refreshPurokOptions() {
            var ps = el('coveragePurokSelect');
            if (!ps) {
                return;
            }
            ps.innerHTML = '';
            var ph = document.createElement('option');
            ph.value = '';
            ph.textContent = '— Optional purok (choose “From barangay” first) —';
            ps.appendChild(ph);
            var v = fromSel && fromSel.value ? fromSel.value.trim() : '';
            var d = decodeCovOpt(v);
            if (!d && state.municipality && v && !state.corridorPresetKey) {
                d = {
                    municipality: state.municipality,
                    province: state.province || '',
                    barangay: v,
                };
            }
            if (!d || typeof window.listPurokLabelsForBarangayCell !== 'function') {
                ps.disabled = true;
                return;
            }
            var labels = window.listPurokLabelsForBarangayCell(
                d.municipality,
                d.province,
                d.barangay
            );
            ps.disabled = labels.length === 0;
            labels.forEach(function (lbl) {
                var o = document.createElement('option');
                o.value = lbl;
                o.textContent = lbl;
                ps.appendChild(o);
            });
        }

        function applyCorridorItems(presetKey, presetLabel, items) {
            state.corridorPresetKey = presetKey || '';
            state.corridorPresetDisplay = presetLabel || '';
            state.municipality = presetLabel || '';
            state.province = '';
            state.labels = [];
            fillSelectCorridor(fromSel, items);
            fillSelectCorridor(toSel, items);
            mirrorToOptions(fromSel, toSel);
            if (pickRow) {
                pickRow.hidden = !(items && items.length);
            }
            if (munRow) {
                munRow.hidden = true;
            }
            if (brgyHintEl) {
                if (items && items.length) {
                    brgyHintEl.hidden = false;
                    brgyHintEl.classList.remove('text-danger');
                    brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                } else {
                    brgyHintEl.hidden = true;
                }
            }
            refreshPurokOptions();
            updatePreview();
            sanitizeDuplicateFromTo();
        }

        function clearCorridorSelection() {
            state.corridorPresetKey = '';
            state.corridorPresetDisplay = '';
            if (corridorPresetSel) {
                corridorPresetSel.value = '';
            }
        }

        function setMsg(txt, isError) {
            if (!msgEl) {
                return;
            }
            if (!txt) {
                msgEl.hidden = true;
                msgEl.textContent = '';
                msgEl.classList.remove('text-danger');
                return;
            }
            msgEl.hidden = false;
            msgEl.textContent = txt;
            if (isError) {
                msgEl.classList.add('text-danger');
            } else {
                msgEl.classList.remove('text-danger');
            }
            if (typeof msgEl.scrollIntoView === 'function') {
                try {
                    msgEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } catch (eScr) {
                    void eScr;
                }
            }
        }

        function updatePreview() {
            var fromIdx = fromSel ? fromSel.selectedIndex : 0;
            var toIdx = toSel ? toSel.selectedIndex : 0;
            var fromTxt =
                fromSel && fromIdx > 0 && fromSel.options[fromIdx]
                    ? fromSel.options[fromIdx].textContent.trim()
                    : '';
            var toTxt =
                toSel && toIdx > 0 && toSel.options[toIdx]
                    ? toSel.options[toIdx].textContent.trim()
                    : '';
            var head =
                state.corridorPresetDisplay ||
                (state.municipality
                    ? state.municipality +
                      (state.province ? ', ' + state.province : '')
                    : '');
            if (preview && head && fromTxt && toTxt) {
                preview.hidden = false;
                preview.textContent = head + ': ' + fromTxt + ' → ' + toTxt;
            } else if (preview) {
                preview.hidden = true;
                preview.textContent = '';
            }
        }

        function sanitizeDuplicateFromTo() {
            if (!fromSel || !toSel) {
                return;
            }
            var f = (fromSel.value || '').trim();
            var t = (toSel.value || '').trim();
            if (f && t && f === t) {
                toSel.value = '';
                if (brgyHintEl) {
                    brgyHintEl.hidden = false;
                    brgyHintEl.classList.add('text-danger');
                    brgyHintEl.textContent =
                        'From and To cannot be the same barangay. Choose a different destination.';
                }
                return;
            }
            if (
                brgyHintEl &&
                brgyHintEl.classList.contains('text-danger')
            ) {
                brgyHintEl.classList.remove('text-danger');
                brgyHintEl.textContent = DEFAULT_BRGY_HINT;
            }
        }

        function finishBarangayList(labels, msgOpts) {
            msgOpts = msgOpts || {};
            clearCorridorSelection();
            state.labels = normalizeBarangayLabels(labels || []);
            fillSelect(fromSel, state.labels);
            fillSelect(toSel, state.labels);
            mirrorToOptions(fromSel, toSel);
            if (pickRow) {
                pickRow.hidden = state.labels.length === 0;
            }
            if (brgyHintEl) {
                if (state.labels.length) {
                    brgyHintEl.hidden = false;
                    brgyHintEl.classList.remove('text-danger');
                    brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                } else {
                    brgyHintEl.hidden = true;
                    brgyHintEl.classList.remove('text-danger');
                    brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                }
            }
            sanitizeDuplicateFromTo();
            if (!msgOpts.skipMsgs) {
                if (state.labels.length) {
                    setMsg(
                        'Showing ' +
                            state.labels.length +
                            ' barangays for ' +
                            state.municipality +
                            (state.province ? ', ' + state.province : '') +
                            '. Choose From barangay and To barangay below.'
                    );
                    if (pickRow && typeof pickRow.scrollIntoView === 'function') {
                        try {
                            pickRow.scrollIntoView({
                                behavior: 'smooth',
                                block: 'nearest',
                            });
                        } catch (eSc) {
                            void eSc;
                        }
                    }
                    if (fromSel && typeof fromSel.focus === 'function') {
                        try {
                            fromSel.focus({ preventScroll: true });
                        } catch (eF) {
                            try {
                                fromSel.focus();
                            } catch (eF2) {
                                void eF2;
                            }
                        }
                    }
                } else if (!msgOpts.fromHttpFail) {
                    setMsg(
                        'No barangays are catalogued for this municipality yet.',
                        true
                    );
                }
            }
            refreshPurokOptions();
            updatePreview();
        }

        function applyMunicipalityChoice(municipality, province) {
            state.municipality = municipality || '';
            state.province = province || '';
            if (useCatalogueApi) {
                var cacheKey = state.municipality + '\n' + (state.province || '');
                if (barangaysCache[cacheKey]) {
                    finishBarangayList(barangaysCache[cacheKey]);
                    return;
                }
                beginCatalogueLoading('barangays');
                var u =
                    coverageBarangaysUrl +
                    '?municipality=' +
                    encodeURIComponent(state.municipality) +
                    '&province=' +
                    encodeURIComponent(state.province || '');
                fetchCatalogueJson(u)
                    .then(function (res) {
                        if (!res.parseOk || res.data === null) {
                            setMsg(
                                'Could not load barangays: server returned a non-JSON reply (HTTP ' +
                                    res.status +
                                    '). Refresh the page or sign in again, then retry.',
                                true
                            );
                            finishBarangayList([], {
                                skipMsgs: true,
                                fromHttpFail: true,
                            });
                            return;
                        }
                        var outData = res.data;
                        if (!res.okHttp || !outData || !outData.ok) {
                            var err =
                                (outData &&
                                    (outData.error ||
                                        outData.message)) ||
                                'Could not load barangays.';
                            setMsg(err, true);
                            finishBarangayList([], {
                                skipMsgs: true,
                                fromHttpFail: true,
                            });
                            return;
                        }
                        if (outData.empty_catalogue) {
                            setMsg(
                                'Address catalogue is empty on the server. Deploy static/generated/address_psgc_negros.generated.js.',
                                true
                            );
                            finishBarangayList([], { skipMsgs: true, fromHttpFail: true });
                            return;
                        }
                        barangaysCache[cacheKey] = normalizeBarangayLabels(
                            outData.barangays || []
                        );
                        finishBarangayList(barangaysCache[cacheKey]);
                    })
                    .catch(function (err) {
                        var timedOut = err && err.name === 'AbortError';
                        setMsg(
                            timedOut
                                ? 'Loading barangays timed out. Check your connection and try again.'
                                : 'Could not load barangays. Check your connection.',
                            true
                        );
                        finishBarangayList([], { skipMsgs: true, fromHttpFail: true });
                    })
                    .finally(endCatalogueLoading);
                return;
            }
            if (typeof window.listCoverageBarangaysInMunicipality !== 'function') {
                setMsg(
                    'Address catalogue not ready. Reload the page and try again.',
                    true
                );
                return;
            }
            finishBarangayList(
                window.listCoverageBarangaysInMunicipality(municipality, province),
                {}
            );
        }

        function populateMunicipalityPicker(matched) {
            state.multi = matched || [];
            if (!munRow || !munSel) {
                return;
            }
            if (!state.multi.length) {
                munRow.hidden = true;
                munSel.innerHTML = '';
                munSel.disabled = true;
                return;
            }

            munRow.hidden = state.multi.length < 2;
            munSel.innerHTML = '';
            var ph = document.createElement('option');
            ph.value = '';
            ph.textContent =
                state.multi.length >= 2
                    ? 'Select city / municipality…'
                    : '—';
            munSel.appendChild(ph);

            state.multi.forEach(function (m, idx) {
                var o = document.createElement('option');
                o.value = String(idx);
                o.textContent = m.municipality + ', ' + (m.province || '');
                o.setAttribute('data-municipality', m.municipality);
                o.setAttribute(
                    'data-province',
                    m.province != null ? m.province : ''
                );
                munSel.appendChild(o);
            });
            munSel.disabled = state.multi.length < 2;

            if (state.multi.length === 1) {
                applyMunicipalityChoice(
                    state.multi[0].municipality,
                    state.multi[0].province
                );
            } else {
                if (brgyHintEl) {
                    brgyHintEl.hidden = true;
                    brgyHintEl.classList.remove('text-danger');
                    brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                }
                if (pickRow) {
                    pickRow.hidden = true;
                }
                fillSelect(fromSel, []);
                fillSelect(toSel, []);
                state.municipality = '';
                updatePreview();
                setMsg(
                    'Several areas matched. Pick the correct city/municipality first.'
                );
            }
        }

        function decodeMunicipalitySelect() {
            if (!munSel || munSel.value === '') {
                return null;
            }
            var opt = munSel.options[munSel.selectedIndex];
            if (!opt) {
                return null;
            }
            return {
                municipality: opt.getAttribute('data-municipality') || '',
                province: opt.getAttribute('data-province') || '',
            };
        }

        function doLoadPlaces(opts) {
            opts = opts || {};
            var silentEmpty = !!opts.silentEmpty;
            var q = placeIn && placeIn.value ? placeIn.value.trim() : '';
            if (!q) {
                if (!silentEmpty) {
                    alert(
                        'Type an area such as Bayawan, Dumaguete, Sipalay, or Santa Catalina.'
                    );
                }
                return;
            }
            clearCorridorSelection();
            if (useCatalogueApi) {
                setMsg('Searching areas…', false);
                var qKey = q.toLowerCase();
                var cachedMun = municipalitiesCache[qKey];
                if (Array.isArray(cachedMun) && cachedMun.length > 0) {
                    populateMunicipalityPicker(cachedMun);
                    return;
                }
                beginCatalogueLoading('search');
                var u = coverageMunicipalitiesUrl + '?q=' + encodeURIComponent(q);
                fetchCatalogueJson(u)
                    .then(function (res) {
                        if (!res.parseOk || res.data === null) {
                            setMsg(
                                'Coverage search failed: expected JSON but got HTTP ' +
                                    res.status +
                                    '. Try refreshing this page or signing in again.',
                                true
                            );
                            return;
                        }
                        var outData = res.data;
                        if (!res.okHttp || !outData || !outData.ok) {
                            var err =
                                (outData &&
                                    (outData.error || outData.message)) ||
                                'Could not load areas.';
                            setMsg(err, true);
                            return;
                        }
                        if (outData.empty_catalogue) {
                            setMsg(
                                'Address catalogue is empty on the server. Deploy static/generated/address_psgc_negros.generated.js.',
                                true
                            );
                            return;
                        }
                        var matched = outData.municipalities || [];
                        if (
                            matched.length === 1 &&
                            Array.isArray(outData.barangays)
                        ) {
                            var m0 = matched[0];
                            var preKey =
                                (m0.municipality || '') +
                                '\n' +
                                (m0.province != null ? m0.province : '');
                            barangaysCache[preKey] = normalizeBarangayLabels(
                                outData.barangays || []
                            );
                        }
                        if (!matched.length) {
                            if (munRow) {
                                munRow.hidden = true;
                            }
                            if (munSel) {
                                munSel.innerHTML = '';
                                munSel.disabled = true;
                            }
                            if (pickRow) {
                                pickRow.hidden = true;
                            }
                            if (brgyHintEl) {
                                brgyHintEl.hidden = true;
                                brgyHintEl.classList.remove('text-danger');
                                brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                            }
                            fillSelect(fromSel, []);
                            fillSelect(toSel, []);
                            state.municipality = '';
                            updatePreview();
                            setMsg(
                                'No municipality match for “' +
                                    q +
                                    '”. Try “Bayawan”, “Basay”, “Sipalay City”, or “City of Bayawan”.',
                                true
                            );
                            return;
                        }
                        municipalitiesCache[qKey] = matched;
                        populateMunicipalityPicker(matched);
                    })
                    .catch(function (err) {
                        var timedOut = err && err.name === 'AbortError';
                        setMsg(
                            timedOut
                                ? 'Coverage search timed out. Check your connection and try again.'
                                : 'Coverage search failed. Check your connection.',
                            true
                        );
                    })
                    .finally(endCatalogueLoading);
                return;
            }
            if (typeof window.findCoverageMunicipalitiesMatching !== 'function') {
                alert(
                    'Address catalogue did not load. Hard-refresh (Ctrl+Shift+R). In DevTools → Network, confirm /static/generated/address_psgc_negros.generated.js and /static/addresses.js load with status 200—not an offline/cached error page.'
                );
                return;
            }
            if (
                typeof window.__ADDRESS_CATALOGUE_ROWS__ === 'number' &&
                window.__ADDRESS_CATALOGUE_ROWS__ <= 0
            ) {
                alert(
                    'The barangay list is empty. The PSGC script did not load or run. Hard-refresh this page. If you use the installed PWA, try Application → Service Workers → unregister, then reload.'
                );
                setMsg(
                    'Address data missing: ensure address_psgc_negros.generated.js loads before addresses.js (see browser console).',
                    true
                );
                return;
            }
            var matched = window.findCoverageMunicipalitiesMatching(q);
            if (!matched.length) {
                if (munRow) {
                    munRow.hidden = true;
                }
                if (munSel) {
                    munSel.innerHTML = '';
                    munSel.disabled = true;
                }
                if (pickRow) {
                    pickRow.hidden = true;
                }
                if (brgyHintEl) {
                    brgyHintEl.hidden = true;
                    brgyHintEl.classList.remove('text-danger');
                    brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                }
                fillSelect(fromSel, []);
                fillSelect(toSel, []);
                state.municipality = '';
                updatePreview();
                setMsg(
                    'No municipality match for “' +
                        q +
                        '”. Try “Bayawan”, “Basay”, or “Sipalay City”.',
                    true
                );
                return;
            }
            populateMunicipalityPicker(matched);
        }

        if (corridorPresetSel && coverageCorridorBarangaysUrl) {
            corridorPresetSel.addEventListener('change', function () {
                var pk = (corridorPresetSel.value || '').trim();
                if (!pk) {
                    clearCorridorSelection();
                    state.municipality = '';
                    state.province = '';
                    state.labels = [];
                    fillSelect(fromSel, []);
                    fillSelect(toSel, []);
                    if (pickRow) {
                        pickRow.hidden = true;
                    }
                    if (brgyHintEl) {
                        brgyHintEl.hidden = true;
                        brgyHintEl.classList.remove('text-danger');
                        brgyHintEl.textContent = DEFAULT_BRGY_HINT;
                    }
                    refreshPurokOptions();
                    updatePreview();
                    setMsg('', false);
                    return;
                }
                var sep = coverageCorridorBarangaysUrl.indexOf('?') >= 0 ? '&' : '?';
                fetch(
                    coverageCorridorBarangaysUrl + sep + 'preset=' + encodeURIComponent(pk)
                )
                    .then(function (r) {
                        return r.json();
                    })
                    .then(function (j) {
                        if (!j || !j.ok) {
                            setMsg(
                                (j && (j.message || j.error)) ||
                                    'Could not load corridor barangays.',
                                true
                            );
                            return;
                        }
                        if (j.empty_catalogue) {
                            setMsg(
                                'Address catalogue is empty on the server. Deploy static/generated/address_psgc_negros.generated.js.',
                                true
                            );
                            applyCorridorItems(
                                pk,
                                j.preset_label || pk,
                                []
                            );
                            return;
                        }
                        applyCorridorItems(
                            pk,
                            j.preset_label || pk,
                            j.items || []
                        );
                        setMsg(
                            'Loaded ' +
                                (j.count || 0) +
                                ' barangays for this corridor. Choose From / To.',
                            false
                        );
                    })
                    .catch(function () {
                        setMsg('Network error loading corridor barangays.', true);
                    });
            });
        }

        if (munSel) {
            munSel.addEventListener('change', function () {
                var info = decodeMunicipalitySelect();
                if (!info || !info.municipality) {
                    return;
                }
                applyMunicipalityChoice(info.municipality, info.province);
            });
        }

        if (fromSel) {
            fromSel.addEventListener('change', function () {
                mirrorToOptions(fromSel, toSel);
                sanitizeDuplicateFromTo();
                refreshPurokOptions();
                updatePreview();
            });
        }
        if (toSel) {
            toSel.addEventListener('change', function () {
                sanitizeDuplicateFromTo();
                updatePreview();
            });
        }

        var purokSel = el('coveragePurokSelect');
        if (purokSel && kwExtra) {
            purokSel.addEventListener('change', function () {
                var chunk = (purokSel.value || '').trim();
                if (!chunk) {
                    return;
                }
                var cur = (kwExtra.value || '').trim();
                if (cur.indexOf(chunk) !== -1) {
                    purokSel.value = '';
                    return;
                }
                kwExtra.value = cur ? cur + ', ' + chunk : chunk;
                purokSel.value = '';
            });
        }

        function resetSingleMunicipalityPickersUi() {
            resetCatalogueLoading();
            if (munRow) {
                munRow.hidden = true;
            }
            if (munSel) {
                munSel.innerHTML = '';
                munSel.disabled = true;
            }
            if (pickRow) {
                pickRow.hidden = true;
            }
            if (brgyHintEl) {
                brgyHintEl.hidden = true;
                brgyHintEl.classList.remove('text-danger');
                brgyHintEl.textContent = DEFAULT_BRGY_HINT;
            }
            fillSelect(fromSel, []);
            fillSelect(toSel, []);
            state.municipality = '';
            state.province = '';
            state.labels = [];
            state.multi = [];
            updatePreview();
        }

        if (placeIn) {
            placeIn.addEventListener('input', function () {
                var q = placeIn.value ? placeIn.value.trim() : '';
                if (!q) {
                    if (!state.corridorPresetKey) {
                        resetSingleMunicipalityPickersUi();
                    } else {
                        resetCatalogueLoading();
                    }
                    setMsg('', false);
                    return;
                }
                if (state.corridorPresetKey) {
                    clearCorridorSelection();
                    resetSingleMunicipalityPickersUi();
                } else {
                    resetSingleMunicipalityPickersUi();
                }
                setMsg(
                    'Click “Search” (or press Enter) to load all barangays for this city or municipality.'
                );
            });
            placeIn.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    doLoadPlaces({ silentEmpty: true });
                }
            });
        }
        if (loadBtn) {
            loadBtn.addEventListener('click', function () {
                doLoadPlaces();
            });
        }

        function submitCreate() {
            if (!createUrl) {
                alert('Create route endpoint not configured.');
                return;
            }
            var fromB = fromSel && fromSel.value ? fromSel.value.trim() : '';
            var toB = toSel && toSel.value ? toSel.value.trim() : '';
            if (fromB && toB && fromB === toB) {
                alert('From and To must be two different barangays.');
                return;
            }
            var fd = decodeBarangayChoice(fromB);
            var td = decodeBarangayChoice(toB);

            if (!fd || !td || !fd.barangay || !td.barangay) {
                alert(
                    'Load barangays (or choose a corridor preset), then choose both “from” and “to” barangays.'
                );
                return;
            }

            var head =
                state.corridorPresetDisplay ||
                (state.municipality
                    ? state.municipality +
                      (state.province ? ', ' + state.province : '')
                    : '');
            if (!head) {
                alert('Search for an area or pick a corridor preset first.');
                return;
            }

            var fromIdx = fromSel ? fromSel.selectedIndex : -1;
            var toIdx = toSel ? toSel.selectedIndex : -1;
            var fromLbl =
                fromSel && fromIdx > 0 && fromSel.options[fromIdx]
                    ? fromSel.options[fromIdx].textContent.trim()
                    : '';
            var toLbl =
                toSel && toIdx > 0 && toSel.options[toIdx]
                    ? toSel.options[toIdx].textContent.trim()
                    : '';
            var label = head + ': ' + fromLbl + ' → ' + toLbl;
            if (label.length > 200) {
                label = label.slice(0, 197) + '…';
            }
            var extras = kwExtra && kwExtra.value ? kwExtra.value.trim() : '';
            var keywords = buildKeywordsDecoded(fd, td, extras);

            var btn = saveBtn;
            if (btn) {
                btn.disabled = true;
            }

            var body = JSON.stringify({
                label: label,
                keywords: keywords,
                csrf_token: csrfFn() || '',
            });
            var headers = { Accept: 'application/json' };
            if (apiHeadersFn) {
                var h = apiHeadersFn();
                Object.assign(headers, h);
            }
            if (!headers['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }
            try {
                var tkn = csrfFn();
                if (tkn) {
                    headers['X-CSRFToken'] = tkn;
                }
            } catch (e2) {
                void e2;
            }

            fetch(createUrl, {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin',
                body: body,
            })
                .then(function (r) {
                    return r
                        .json()
                        .then(function (data) {
                            return { ok: r.ok, data: data };
                        })
                        .catch(function () {
                            return {
                                ok: r.ok,
                                data: { error: 'Invalid response from server.' },
                            };
                        });
                })
                .then(function (out) {
                    if (btn) {
                        btn.disabled = false;
                    }
                    if (out.ok && out.data && out.data.success) {
                        location.reload();
                        return;
                    }
                    var msg =
                        (out.data &&
                            (out.data.message || out.data.error)) ||
                        'Could not create route';
                    alert(msg);
                })
                .catch(function () {
                    if (btn) {
                        btn.disabled = false;
                    }
                    alert('Could not create route. Check your connection.');
                });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', function (ev) {
                ev.preventDefault();
                submitCreate();
            });
        }
    };
})();
