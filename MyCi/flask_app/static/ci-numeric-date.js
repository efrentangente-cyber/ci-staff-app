/**
 * CI interview date fields: numeric-only display (YYYY-MM-DD) for WebView/Android where
 * type="date" pickers show localized month names.
 */
(function () {
  'use strict';

  function digitsToYmd(digits) {
    var d = String(digits || '').replace(/\D/g, '').slice(0, 8);
    var out = '';
    if (d.length) out = d.slice(0, 4);
    if (d.length >= 5) out += '-' + d.slice(4, 6);
    if (d.length >= 7) out += '-' + d.slice(6, 8);
    return out;
  }

  function todayIso() {
    var n = new Date();
    return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0');
  }

  /** Accept ISO, DD-MM-YYYY, DD/MM/YYYY, or Date.parse; return YYYY-MM-DD or ''. */
  function toIsoFromLoose(s) {
    if (s == null || s === '') return '';
    s = String(s).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    var m = /^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})$/.exec(s);
    if (m) {
      var dd = parseInt(m[1], 10);
      var mo = parseInt(m[2], 10);
      var yy = parseInt(m[3], 10);
      if (mo >= 1 && mo <= 12 && dd >= 1 && dd <= 31) {
        return yy + '-' + String(mo).padStart(2, '0') + '-' + String(dd).padStart(2, '0');
      }
    }
    m = /^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})$/.exec(s);
    if (m) {
      return m[1] + '-' + m[2].padStart(2, '0') + '-' + m[3].padStart(2, '0');
    }
    var t = Date.parse(s);
    if (!isNaN(t)) {
      var d = new Date(t);
      return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }
    return '';
  }

  function wire(el) {
    if (!el || el.nodeName !== 'INPUT') return;
    el.setAttribute('type', 'text');
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('autocomplete', 'off');
    el.setAttribute('placeholder', 'YYYY-MM-DD');
    el.setAttribute('maxlength', '10');
    el.setAttribute('pattern', '\\d{4}-\\d{2}-\\d{2}');
    el.setAttribute('title', 'Numbers only: YYYY-MM-DD');
    if (!el.classList.contains('ci-numeric-date')) el.classList.add('ci-numeric-date');
    if (el._ciNumericDateWired) return;
    el._ciNumericDateWired = true;
    el.addEventListener('input', function () {
      var next = digitsToYmd(el.value);
      el.value = next;
      try {
        el.setSelectionRange(next.length, next.length);
      } catch (e) { /* ignore */ }
    });
  }

  function setValue(el, raw) {
    if (!el) return;
    wire(el);
    var iso = toIsoFromLoose(raw);
    if (iso) {
      el.value = iso;
      return;
    }
    if (raw != null && raw !== '') el.value = digitsToYmd(raw);
  }

  window.CiNumericDate = {
    wire: wire,
    setValue: setValue,
    toIso: toIsoFromLoose,
    todayIso: todayIso
  };

  function boot() {
    document.querySelectorAll('#interview_date, input[data-ci-numeric-date]').forEach(wire);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
