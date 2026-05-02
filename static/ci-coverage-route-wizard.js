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

    /** From/to barangays + extras only — no city/province (would match every applicant in that area). */
    function buildKeywords(fromB, toB, extraCsv) {
        var kws = [];
        function add(s) {
            var t = String(s || '').trim().toLowerCase();
            if (!t || kws.indexOf(t) >= 0) {
                return;
            }
            kws.push(t);
        }
        add(fromB);
        add(toB);
        (extraCsv || '').split(',').forEach(function (x) {
            add(x.trim());
        });
        return kws;
    }

    window.initCiCoverageRouteWizard = function (opts) {
        var wrap = opts && opts.rootId ? el(opts.rootId) : el('ciCoverageRouteWizard');
        if (!wrap) {
            return;
        }

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

        var state = {
            municipality: '',
            province: '',
            labels: [],
            multi: [],
        };

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
        }

        function updatePreview() {
            var fromB = fromSel && fromSel.value ? fromSel.value : '';
            var toB = toSel && toSel.value ? toSel.value : '';
            if (preview && state.municipality && fromB && toB) {
                preview.hidden = false;
                preview.textContent =
                    state.municipality + ': ' + fromB + ' → ' + toB;
            } else if (preview) {
                preview.hidden = true;
                preview.textContent = '';
            }
        }

        function finishBarangayList(labels) {
            state.labels = labels || [];
            fillSelect(fromSel, state.labels);
            fillSelect(toSel, state.labels);
            mirrorToOptions(fromSel, toSel);
            if (pickRow) {
                pickRow.hidden = state.labels.length === 0;
            }
            if (state.labels.length) {
                setMsg(
                    'Showing ' +
                        state.labels.length +
                        ' barangays under ' +
                        state.municipality +
                        ' (' +
                        state.province +
                        '). Choose from / to.'
                );
            } else {
                setMsg(
                    'No barangays are catalogued for this municipality yet.',
                    true
                );
            }
            updatePreview();
        }

        function applyMunicipalityChoice(municipality, province) {
            state.municipality = municipality || '';
            state.province = province || '';
            if (useCatalogueApi) {
                setMsg('Loading barangays…', false);
                var u =
                    coverageBarangaysUrl +
                    '?municipality=' +
                    encodeURIComponent(state.municipality) +
                    '&province=' +
                    encodeURIComponent(state.province || '');
                fetch(u, {
                    credentials: 'same-origin',
                    headers: catalogueFetchHeaders(),
                })
                    .then(function (r) {
                        return r.json().then(function (data) {
                            return { ok: r.ok, data: data };
                        });
                    })
                    .then(function (out) {
                        if (!out.ok || !out.data || !out.data.ok) {
                            var err =
                                (out.data && (out.data.error || out.data.message)) ||
                                'Could not load barangays.';
                            setMsg(err, true);
                            finishBarangayList([]);
                            return;
                        }
                        if (out.data.empty_catalogue) {
                            setMsg(
                                'Address catalogue is empty on the server. Deploy static/generated/address_psgc_negros.generated.js.',
                                true
                            );
                            finishBarangayList([]);
                            return;
                        }
                        finishBarangayList(out.data.barangays || []);
                    })
                    .catch(function () {
                        setMsg('Could not load barangays. Check your connection.', true);
                        finishBarangayList([]);
                    });
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
                window.listCoverageBarangaysInMunicipality(municipality, province)
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

        function doLoadPlaces() {
            var q = placeIn && placeIn.value ? placeIn.value.trim() : '';
            if (!q) {
                alert(
                    'Type an area such as Bayawan, Dumaguete, Sipalay, or Santa Catalina.'
                );
                return;
            }
            if (useCatalogueApi) {
                if (loadBtn) {
                    loadBtn.disabled = true;
                }
                var u = coverageMunicipalitiesUrl + '?q=' + encodeURIComponent(q);
                fetch(u, {
                    credentials: 'same-origin',
                    headers: catalogueFetchHeaders(),
                })
                    .then(function (r) {
                        return r.json().then(function (data) {
                            return { ok: r.ok, data: data };
                        });
                    })
                    .then(function (out) {
                        if (loadBtn) {
                            loadBtn.disabled = false;
                        }
                        if (!out.ok || !out.data || !out.data.ok) {
                            var err =
                                (out.data && (out.data.error || out.data.message)) ||
                                'Could not load areas.';
                            alert(err);
                            return;
                        }
                        if (out.data.empty_catalogue) {
                            setMsg(
                                'Address catalogue is empty on the server. Deploy static/generated/address_psgc_negros.generated.js.',
                                true
                            );
                            return;
                        }
                        var matched = out.data.municipalities || [];
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
                        if (matched.length === 1) {
                            setMsg('');
                        }
                    })
                    .catch(function () {
                        if (loadBtn) {
                            loadBtn.disabled = false;
                        }
                        alert('Could not load areas. Check your connection.');
                    });
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
            if (matched.length === 1) {
                setMsg('');
            }
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
                updatePreview();
            });
        }
        if (toSel) {
            toSel.addEventListener('change', updatePreview);
        }

        if (placeIn) {
            placeIn.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    doLoadPlaces();
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
            var mun = state.municipality;
            var prov = state.province;
            var fromB = fromSel && fromSel.value ? fromSel.value.trim() : '';
            var toB = toSel && toSel.value ? toSel.value.trim() : '';

            if (!mun || !fromB || !toB) {
                alert(
                    'Search for an area, load barangays, then choose both “from” and “to” barangays.'
                );
                return;
            }

            var label =
                mun + ': ' + fromB + ' → ' + toB;
            if (label.length > 200) {
                label = label.slice(0, 197) + '…';
            }
            var extras = kwExtra && kwExtra.value ? kwExtra.value.trim() : '';
            var keywords = buildKeywords(fromB, toB, extras);

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
