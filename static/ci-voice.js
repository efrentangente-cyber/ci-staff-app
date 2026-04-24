/**
 * CI/BI: Web Speech API → text into search fields or the focused form control.
 * Requires HTTPS in most browsers. Uses en-PH / en-US fallback.
 */
(function () {
  'use strict';
  if (typeof window === 'undefined') return;
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    window.__ciVoiceSupported = false;
    return;
  }
  window.__ciVoiceSupported = true;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  let lastRecognition = null;

  function stopIfRunning() {
    if (lastRecognition) {
      try { lastRecognition.stop(); } catch (e) { /* ignore */ }
      lastRecognition = null;
    }
  }

  /**
   * Put transcript into an input, trigger input/change, optional callback.
   * @param {string} inputId
   * @param {function} [after] e.g. () => searchApplications('pending')
   */
  window.ciVoiceToInput = function (inputId, after) {
    const el = document.getElementById(inputId);
    if (!el) return;
    stopIfRunning();
    const rec = new SpeechRecognition();
    lastRecognition = rec;
    rec.lang = 'en-PH';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = function (event) {
      const transcript = (event.results[0] && event.results[0][0] && event.results[0][0].transcript) || '';
      if (!transcript) return;
      const cur = (el.value || '').trim();
      el.value = cur ? cur + ' ' + transcript : transcript;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      if (el.oninput) {
        try { el.oninput(new Event('input')); } catch (e) { /* ignore */ }
      }
      if (typeof after === 'function') {
        try { after(); } catch (e) { /* ignore */ }
      }
    };
    rec.onerror = function (ev) {
      if (ev.error === 'not-allowed') {
        window.alert('Microphone is blocked. Allow microphone in the browser for voice input.');
      } else if (ev.error !== 'aborted' && ev.error !== 'no-speech') {
        window.alert('Voice did not work: ' + (ev.error || 'unknown'));
      }
    };
    rec.onend = function () { lastRecognition = null; };
    try {
      rec.start();
    } catch (e) {
      window.alert('Could not start voice. Try again.');
    }
  };

  /**
   * Append dictation to the currently focused input, textarea, or contenteditable; otherwise show hint.
   */
  window.ciVoiceToFocusedField = function () {
    const el = document.activeElement;
    if (!el) {
      window.alert('Tap a form field (text box) first, then use voice.');
      return;
    }
    const tag = (el.tagName || '').toLowerCase();
    if (tag !== 'input' && tag !== 'textarea' && el.isContentEditable !== true) {
      window.alert('Tap a text or number field first, then use voice again.');
      return;
    }
    if (el.type && ['button', 'submit', 'hidden', 'checkbox', 'radio', 'file'].indexOf(el.type) !== -1) {
      window.alert('Focus a text field, then use voice again.');
      return;
    }
    stopIfRunning();
    const rec = new SpeechRecognition();
    lastRecognition = rec;
    rec.lang = 'en-PH';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = function (event) {
      const transcript = (event.results[0] && event.results[0][0] && event.results[0][0].transcript) || '';
      if (!transcript) return;
      if (el.isContentEditable) {
        el.textContent = (el.textContent || '').trim() + (el.textContent ? ' ' : '') + transcript;
      } else {
        const cur = (el.value || '').trim();
        el.value = cur ? cur + ' ' + transcript : transcript;
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      if (el.onchange) {
        try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) { /* ignore */ }
      }
    };
    rec.onerror = function (ev) {
      if (ev.error === 'not-allowed') {
        window.alert('Allow microphone in your browser to use voice on this form.');
      }
    };
    rec.onend = function () { lastRecognition = null; };
    try { rec.start(); } catch (e) {
      window.alert('Could not start voice. Try again.');
    }
  };
})();
