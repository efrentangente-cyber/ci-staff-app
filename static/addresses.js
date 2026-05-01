// Address rows for loan forms + coverage-route wizard (Negros Oriental & Occidental).
// Barangays: PSGC-derived list in static/generated/address_psgc_negros.generated.js (see tools/build_negros_psgc_address_js.py).
// Puroks: PSGC does not define puroks nationwide. We add:
//   (1) ADDRESS_PUROK_OVERRIDES — curated names per barangay
//   (2) BAYAWAN_REFERENCED_SUBDIVISIONS — sitios / local labels cited in Wikipedia (Bayawan) + DepEd NIR Bayawan City school placenames
//   (3) Numbered fillers "Purok 1"…"Purok N" for gaps (deduped with named lists).

/** Default numbered purok rows per barangay outside Bayawan City core. */
const SYNTHETIC_PUROK_MAX = 25;

/** City of Bayawan (Negros Oriental): more numbered quick-picks — field forms commonly use >25 purok labels. */
const SYNTHETIC_PUROK_MAX_BAYAWAN_ORIENTAL = 55;

/**
 * Optional purok names per barangay. Keys must match PSGC municipality + province strings exactly.
 * Barangay keys must match PSGC barangay names exactly.
 */
const ADDRESS_PUROK_OVERRIDES = {
    'City of Bayawan|Negros Oriental': {
        Villareal: [
            'Purok 1', 'Purok 2', 'Purok 3', 'Purok 4', 'Purok 5',
            'Purok 6', 'Purok 7', 'Purok 8', 'Purok 9', 'Purok 10',
            'Purok Pagkakaisa', 'Purok Sampaguita', 'Purok Gemelina',
        ],
    },
};

/**
 * City of Bayawan only (PSGC barangay keys). Compiled from Wikipedia "Bayawan" (Education /
 * Infrastructure) and visible DepEd NIR Bayawan rows (school names as local toponyms). Not an
 * official barangay purok master list — LGU/IP pages can extend ADDRESS_PUROK_OVERRIDES.
 */
const BAYAWAN_REFERENCED_SUBDIVISIONS = {
    Banga: [
        'Cabcabon Hills',
        'Buli-Buli',
        'Sitio Buli-Buli',
        'Cansig-id',
        'Sitio Cansig-id',
    ],
    Bugay: ['Baican', 'Purok Baican', 'Sitio Baican', 'Bahian', 'Sitio Bahian'],
    Dawis: ['Lapay', 'Sitio Lapay', 'Purok Lapay'],
    Kalumboyan: ['Baisan', 'Sitio Baisan'],
    Malabugas: ['Tinastasan', 'Sitio Tinastasan'],
    Maninihon: ['Omod', 'Sitio Omod', 'Purok Omod', 'Pusi-on', 'Sitio Pusi-on'],
    Mandu-ao: ['Manduaw'],
    Nangka: [
        'Tavera',
        'Sitio Tavera',
        'Milagrosa',
        'Sitio Milagrosa',
        'Hugno',
        'Danapa',
        'Sitio Danapa',
    ],
    Narra: ['Gamao', 'Sitio Gamao'],
    Tabuan: ['Mantapi', 'Sitio Mantapi'],
    Villasol: ['Purok Baican', 'Baican', 'Sitio Baican', 'Bato'],
};

let addressDatabase = [];

/** Add Purok 1..cap skipping labels already present in usedLower (case-insensitive keys). */
function addSyntheticPurokRowsDeduped(municipality, province, barangay, usedLower, cap) {
    var maxNum =
        typeof cap === 'number' && cap > 0 ? Math.floor(cap) : SYNTHETIC_PUROK_MAX;
    var used = usedLower || {};
    var i;
    for (i = 1; i <= maxNum; i++) {
        var label = 'Purok ' + i;
        var k = label.toLowerCase();
        if (used[k]) {
            continue;
        }
        used[k] = true;
        addressDatabase.push({
            purok: label,
            barangay: barangay,
            municipality: municipality,
            province: province,
            synthetic: true,
        });
    }
}

function __munProvKey(municipality, province) {
    return String(municipality || '').trim() + '|' + String(province || '').trim();
}

function buildAddressDatabaseFromPsgc() {
    var rows = typeof window !== 'undefined' ? window.__PSGC_NEGROS_BARANGAYS__ : null;
    if (!rows || !rows.length) {
        return false;
    }
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        var mun = String(r.municipality || '').trim();
        var prov = String(r.province || '').trim();
        var brgy = String(r.barangay || '').trim();
        if (!mun || !prov || !brgy) {
            continue;
        }
        addressDatabase.push({
            barangay: brgy,
            municipality: mun,
            province: prov,
        });
        var pmap = ADDRESS_PUROK_OVERRIDES[__munProvKey(mun, prov)];
        var plist = pmap && pmap[brgy];
        var usedPurokLower = {};
        var purokCap =
            mun === 'City of Bayawan' && prov === 'Negros Oriental'
                ? SYNTHETIC_PUROK_MAX_BAYAWAN_ORIENTAL
                : SYNTHETIC_PUROK_MAX;

        var namedCombined = [];
        var j;
        if (plist && plist.length) {
            for (j = 0; j < plist.length; j++) {
                namedCombined.push(plist[j]);
            }
        }
        if (mun === 'City of Bayawan' && prov === 'Negros Oriental') {
            var refs = BAYAWAN_REFERENCED_SUBDIVISIONS[brgy];
            if (refs && refs.length) {
                for (j = 0; j < refs.length; j++) {
                    namedCombined.push(refs[j]);
                }
            }
        }

        if (namedCombined.length) {
            for (j = 0; j < namedCombined.length; j++) {
                var rawLbl = String(namedCombined[j] || '').trim();
                if (!rawLbl) {
                    continue;
                }
                var keyLower = rawLbl.toLowerCase();
                if (usedPurokLower[keyLower]) {
                    continue;
                }
                usedPurokLower[keyLower] = true;
                addressDatabase.push({
                    purok: rawLbl,
                    barangay: brgy,
                    municipality: mun,
                    province: prov,
                    synthetic: /^Purok\s+\d+$/i.test(rawLbl),
                });
            }
        }

        addSyntheticPurokRowsDeduped(mun, prov, brgy, usedPurokLower, purokCap);
    }
    return true;
}

if (!buildAddressDatabaseFromPsgc()) {
    console.error(
        'addresses.js: load address_psgc_negros.generated.js BEFORE this file. Run tools/build_negros_psgc_address_js.py if missing.'
    );
}

console.log(
    'Address rows loaded: ' +
        addressDatabase.length +
        ' (PSGC Negros barangays; City of Bayawan NO + overrides + Wikipedia/DepEd-referenced subdivisions where listed + numbered Purok up to ' +
        SYNTHETIC_PUROK_MAX_BAYAWAN_ORIENTAL +
        ' there, ' +
        SYNTHETIC_PUROK_MAX +
        ' elsewhere where not overridden)',
);

/** Coverage route builder — barangays by municipality using addressDatabase */
function findCoverageMunicipalitiesMatching(rawQuery) {
    var q = (rawQuery || '').toLowerCase().trim();
    if (!q) {
        return [];
    }
    function munMatches(rowMunLower, munTrimmed, rawQLower) {
        if (rowMunLower.indexOf(rawQLower) !== -1) {
            return true;
        }
        var shortName = munTrimmed.replace(/^City\s+of\s+/i, '').trim();
        if (!shortName) {
            return false;
        }
        var shorts = shortName.toLowerCase();
        var aliasCity = shorts + ' city';
        if (aliasCity.indexOf(rawQLower) !== -1 || shorts.indexOf(rawQLower) !== -1) {
            return true;
        }
        /* e.g. user types “city bayawan” */
        var qNorm = rawQLower.replace(/^city\s+of\s+/, '').trim();
        return qNorm.length > 0 && shorts.indexOf(qNorm) !== -1;
    }

    var map = new Map();
    for (var i = 0; i < addressDatabase.length; i++) {
        var row = addressDatabase[i];
        var mun = (row.municipality || '').trim();
        var prov = (row.province || '').trim();
        if (!mun) {
            continue;
        }
        if (!munMatches(mun.toLowerCase(), mun, q)) {
            continue;
        }
        var k = mun + '\n' + prov;
        if (!map.has(k)) {
            map.set(k, { municipality: mun, province: prov });
        }
    }
    return Array.from(map.values()).sort(function (a, b) {
        return a.municipality.localeCompare(b.municipality, undefined, { sensitivity: 'base' });
    });
}

function listCoverageBarangaysInMunicipality(municipality, province) {
    var mun = (municipality || '').trim();
    var prov = (province || '').trim();
    var set = {};
    for (var i = 0; i < addressDatabase.length; i++) {
        var row = addressDatabase[i];
        if ((row.municipality || '').trim() !== mun) {
            continue;
        }
        if (prov && (row.province || '').trim() !== prov) {
            continue;
        }
        var b = (row.barangay || '').trim();
        if (b) {
            set[b] = true;
        }
    }
    return Object.keys(set).sort(function (a, b) {
        return a.localeCompare(b, undefined, { sensitivity: 'base' });
    });
}

window.findCoverageMunicipalitiesMatching = findCoverageMunicipalitiesMatching;
window.listCoverageBarangaysInMunicipality = listCoverageBarangaysInMunicipality;
