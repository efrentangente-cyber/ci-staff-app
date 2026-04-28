/**
 * Compact route assignment UI: replaces a tall <select multiple> with a Bootstrap dropdown
 * (checkbox list). Targets: .route-assign-multiselect, [data-route-assign="compact"], or .ci-route-select.
 *
 * Example:
 *   <select name="assigned_route_ids" multiple class="form-select form-select-sm route-assign-multiselect">...</select>
 */
(function () {
  'use strict';

  function optLabel(opt) {
    return (opt.textContent || opt.value || '').trim();
  }

  function syncCheckbox(select, value, checked) {
    var o = Array.prototype.find.call(select.options, function (x) {
      return x.value === value;
    });
    if (o) {
      o.selected = !!checked;
    }
  }

  function selectedCount(select) {
    var n = 0;
    Array.prototype.forEach.call(select.options, function (o) {
      if (o.selected && o.value) {
        n += 1;
      }
    });
    return n;
  }

  function hideHintNear(select) {
    var el = select.nextElementSibling;
    var guard = 0;
    while (el && guard < 6) {
      guard += 1;
      if (el.matches && el.matches('.route-assign-hint')) {
        el.hidden = true;
        el.classList.add('d-none');
        break;
      }
      if (
        el.matches &&
        el.matches('small.text-muted') &&
        /Ctrl|⌘|multiple/i.test(el.textContent || '')
      ) {
        el.hidden = true;
        el.classList.add('d-none');
        break;
      }
      el = el.nextElementSibling;
    }
  }

  function enhance(select) {
    if (select.dataset.routeAssignEnhanced === '1') {
      return;
    }
    try {
    select.dataset.routeAssignEnhanced = '1';

    var wrap = document.createElement('div');
    wrap.className = 'dropdown route-assign-compact w-100';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-outline-secondary dropdown-toggle w-100 text-start';
    btn.setAttribute('aria-expanded', 'false');

    function updateBtn() {
      var n = selectedCount(select);
      btn.innerHTML =
        '<i class="bi bi-signpost-split" aria-hidden="true"></i> ' +
        (n ? 'Select routes (' + n + ')' : 'Select routes');
      var titles = [];
      Array.prototype.forEach.call(select.options, function (o) {
        if (o.selected && o.value) {
          titles.push(optLabel(o));
        }
      });
      btn.title = titles.length ? titles.join('; ') : 'Open list and tick routes';
    }
    updateBtn();

    var menu = document.createElement('div');
    menu.className = 'dropdown-menu shadow-sm route-assign-dd-menu p-2';
    menu.setAttribute('aria-labelledby', '');
    menu.style.minWidth = '15rem';
    menu.style.maxHeight = '260px';
    menu.style.overflowY = 'auto';

    Array.prototype.forEach.call(select.options, function (opt) {
      if (!opt.value) {
        return;
      }
      var uid = 'rac-' + Math.random().toString(36).slice(2, 11);
      var row = document.createElement('div');
      row.className = 'form-check mb-1 px-1';
      var inp = document.createElement('input');
      inp.type = 'checkbox';
      inp.className = 'form-check-input';
      inp.id = uid;
      inp.setAttribute('data-route-value', opt.value);
      inp.checked = opt.selected;
      var lab = document.createElement('label');
      lab.className = 'form-check-label small';
      lab.setAttribute('for', uid);
      lab.textContent = optLabel(opt);
      row.appendChild(inp);
      row.appendChild(lab);
      menu.appendChild(row);
    });

    var done = document.createElement('button');
    done.type = 'button';
    done.className = 'btn btn-sm btn-outline-secondary w-100 mt-2';
    done.textContent = 'Close';
    menu.appendChild(done);

    function syncDisabledFromSelect() {
      var dis = !!select.disabled;
      btn.disabled = dis;
      menu.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
        cb.disabled = dis;
      });
      done.disabled = dis;
    }

    wrap.appendChild(btn);
    wrap.appendChild(menu);

    if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
      try {
        new bootstrap.Dropdown(btn, {
          autoClose: 'outside',
          boundary: document.body,
          popperConfig: function (defaultBsPopperConfig) {
            defaultBsPopperConfig.strategy = 'fixed';
            return defaultBsPopperConfig;
          }
        });
      } catch (ddErr) {
        console.warn('route-assign Dropdown init:', ddErr);
      }
    }

    select.classList.add('visually-hidden');
    select.classList.remove('route-assign-await-js');
    select.setAttribute('tabindex', '-1');
    select.setAttribute('aria-hidden', 'true');

    select.parentNode.insertBefore(wrap, select);

    hideHintNear(select);
    syncDisabledFromSelect();

    try {
      var mo = new MutationObserver(syncDisabledFromSelect);
      mo.observe(select, { attributes: true, attributeFilter: ['disabled'] });
    } catch (e) {
      void e;
    }

    menu.addEventListener('change', function (ev) {
      var t = ev.target;
      if (!t || t.type !== 'checkbox') {
        return;
      }
      var rv = t.getAttribute('data-route-value');
      if (rv == null || rv === '') {
        return;
      }
      syncCheckbox(select, rv, t.checked);
      updateBtn();
    });

    done.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
        var dd = bootstrap.Dropdown.getInstance(btn);
        if (dd) {
          dd.hide();
        }
      }
    });

    updateBtn();
    } catch (err) {
      console.warn('route-assign-dropdown enhance:', err);
      select.classList.remove('route-assign-await-js');
      select.removeAttribute('data-route-assign-enhanced');
    }
  }

  function init() {
    document
      .querySelectorAll(
        'select.ci-route-select[multiple]:not([data-route-assign-enhanced]), ' +
          'select.route-assign-multiselect[multiple]:not([data-route-assign-enhanced]), ' +
          'select[data-route-assign="compact"][multiple]:not([data-route-assign-enhanced])'
      )
      .forEach(enhance);
  }

  function boot() {
    init();
    window.setTimeout(init, 250);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  window.addEventListener('load', function () {
    window.setTimeout(init, 100);
  });
})();
