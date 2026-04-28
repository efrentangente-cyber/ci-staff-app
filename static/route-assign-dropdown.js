/**
 * Compact route assignment UI: replaces a tall <select multiple> with a Bootstrap dropdown
 * (checkbox list). Add class "route-assign-multiselect" or data-route-assign="compact" on the select.
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
    select.dataset.routeAssignEnhanced = '1';

    var wrap = document.createElement('div');
    wrap.className = 'dropdown route-assign-compact d-inline-block';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-outline-secondary dropdown-toggle';
    btn.setAttribute('data-bs-toggle', 'dropdown');
    btn.setAttribute('data-bs-auto-close', 'outside');
    btn.setAttribute('aria-expanded', 'false');

    function updateBtn() {
      var n = selectedCount(select);
      btn.innerHTML =
        '<i class="bi bi-signpost-split" aria-hidden="true"></i> ' +
        (n ? 'Routes (' + n + ')' : 'Routes');
      var titles = [];
      Array.prototype.forEach.call(select.options, function (o) {
        if (o.selected && o.value) {
          titles.push(optLabel(o));
        }
      });
      btn.title = titles.length ? titles.join('; ') : 'Choose routes';
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
      inp.dataset.routeValue = opt.value;
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
    done.className = 'btn btn-sm btn-primary w-100 mt-2';
    done.textContent = 'Done';
    menu.appendChild(done);

    wrap.appendChild(btn);
    wrap.appendChild(menu);

    select.classList.add('visually-hidden');
    select.setAttribute('tabindex', '-1');
    select.setAttribute('aria-hidden', 'true');

    select.parentNode.insertBefore(wrap, select);

    hideHintNear(select);

    menu.addEventListener('change', function (ev) {
      var t = ev.target;
      if (!t || !t.matches || !t.matches('input[type="checkbox"][data-route-value]')) {
        return;
      }
      syncCheckbox(select, t.getAttribute('data-route-value'), t.checked);
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
  }

  function init() {
    document
      .querySelectorAll(
        'select.route-assign-multiselect[multiple], select[data-route-assign="compact"][multiple]'
      )
      .forEach(enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
