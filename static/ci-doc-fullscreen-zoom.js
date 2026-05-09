/**
 * CI/BI fullscreen image viewer — tap-to-open, pinch zoom, drag pan, ESC/close button.
 */
(function () {
    'use strict';

    var root = null;
    var img = null;
    var layer = null;
    var titleEl = null;
    var state = {
        scale: 1,
        minScale: 1,
        maxScale: 8,
        x: 0,
        y: 0,
        pinching: false,
        pinchDist0: 0,
        scale0: 1,
        panning: false,
        panSx: 0,
        panSy: 0,
        panX0: 0,
        panY0: 0,
    };

    function ensureDom() {
        if (root) {
            return;
        }
        root = document.createElement('div');
        root.id = 'ciDocFullscreenLightbox';
        root.className = 'ci-doc-fs-lightbox';
        root.hidden = true;
        root.setAttribute('role', 'dialog');
        root.setAttribute('aria-modal', 'true');
        root.innerHTML =
            '<div class="ci-doc-fs-backdrop"></div>' +
            '<button type="button" class="ci-doc-fs-close" aria-label="Close">&times;</button>' +
            '<p class="ci-doc-fs-title" aria-live="polite"></p>' +
            '<div class="ci-doc-fs-viewport">' +
            '<div class="ci-doc-fs-layer"><img draggable="false" decoding="async" alt=""></div>' +
            '</div>' +
            '<p class="ci-doc-fs-hint">Pinch (or Ctrl+scroll) to zoom · Drag to move · ESC or tap backdrop to close</p>';
        document.body.appendChild(root);
        titleEl = root.querySelector('.ci-doc-fs-title');
        layer = root.querySelector('.ci-doc-fs-layer');
        img = root.querySelector('img');
        var backdrop = root.querySelector('.ci-doc-fs-backdrop');
        var btnClose = root.querySelector('.ci-doc-fs-close');

        btnClose.addEventListener('click', close);
        backdrop.addEventListener('click', function (ev) {
            if (ev.target === backdrop && state.scale <= 1.02) {
                close();
            }
        });

        document.addEventListener('keydown', onKey);

        viewportEvents(root.querySelector('.ci-doc-fs-viewport'));
        root.addEventListener('wheel', onWheel, { passive: false });
    }

    function onKey(ev) {
        if (!root || root.hidden) {
            return;
        }
        if (ev.key === 'Escape') {
            ev.preventDefault();
            close();
        }
    }

    function resetZoom() {
        state.scale = 1;
        state.x = 0;
        state.y = 0;
        state.pinching = false;
        state.panning = false;
        applyTransform();
    }

    function applyTransform() {
        if (!layer) {
            return;
        }
        layer.style.transform =
            'translate3d(' + state.x + 'px,' + state.y + 'px,0) scale(' + state.scale + ')';
    }

    function distance(touches) {
        var dx = touches[0].clientX - touches[1].clientX;
        var dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy) || 1;
    }

    function clampScale(s) {
        return Math.min(state.maxScale, Math.max(state.minScale, s));
    }

    function viewportEvents(vp) {
        if (!vp) {
            return;
        }
        vp.addEventListener('touchstart', onTouchStart, { passive: false });
        vp.addEventListener('touchmove', onTouchMove, { passive: false });
        vp.addEventListener('touchend', onTouchEnd, { passive: true });

        vp.addEventListener(
            'pointerdown',
            function (e) {
                if (!root || root.hidden || e.pointerType !== 'mouse') {
                    return;
                }
                if ((e.buttons || 1) !== 1) {
                    return;
                }
                if (state.scale <= 1.02) {
                    return;
                }
                state.panning = true;
                state.pinching = false;
                state.panSx = e.clientX;
                state.panSy = e.clientY;
                state.panX0 = state.x;
                state.panY0 = state.y;
                vp.setPointerCapture(e.pointerId);
            },
            true
        );
        vp.addEventListener(
            'pointermove',
            function (e) {
                if (!state.panning || e.pointerType !== 'mouse') {
                    return;
                }
                state.x = state.panX0 + (e.clientX - state.panSx);
                state.y = state.panY0 + (e.clientY - state.panSy);
                applyTransform();
            },
            true
        );
        vp.addEventListener(
            'pointerup pointercancel pointerleave',
            function () {
                state.panning = false;
            },
            true
        );
    }

    function onTouchStart(ev) {
        if (!root || root.hidden) {
            return;
        }
        if (ev.touches.length >= 2) {
            ev.preventDefault();
            state.pinching = true;
            state.panning = false;
            state.pinchDist0 = distance(ev.touches);
            state.scale0 = state.scale;
        } else if (ev.touches.length === 1 && state.scale > 1.02) {
            state.panning = true;
            state.pinching = false;
            state.panSx = ev.touches[0].clientX;
            state.panSy = ev.touches[0].clientY;
            state.panX0 = state.x;
            state.panY0 = state.y;
        }
    }

    function onTouchMove(ev) {
        if (!root || root.hidden) {
            return;
        }
        if (ev.touches.length >= 2) {
            if (!state.pinching) {
                state.pinching = true;
                state.panning = false;
                state.pinchDist0 = distance(ev.touches);
                state.scale0 = state.scale;
            }
            ev.preventDefault();
            var d = distance(ev.touches);
            var ratio = d / state.pinchDist0;
            state.scale = clampScale(state.scale0 * ratio);
            applyTransform();
        } else if (ev.touches.length === 1 && state.panning && !state.pinching) {
            ev.preventDefault();
            var cx = ev.touches[0].clientX;
            var cy = ev.touches[0].clientY;
            state.x = state.panX0 + (cx - state.panSx);
            state.y = state.panY0 + (cy - state.panSy);
            applyTransform();
        }
    }

    function onTouchEnd(ev) {
        if (ev.touches.length < 2) {
            state.pinching = false;
        }
        if (ev.touches.length === 1 && state.scale > 1.02) {
            state.panning = true;
            state.panSx = ev.touches[0].clientX;
            state.panSy = ev.touches[0].clientY;
            state.panX0 = state.x;
            state.panY0 = state.y;
        }
        if (!ev.touches.length) {
            state.panning = false;
        }
        state.scale = clampScale(state.scale);
        applyTransform();
    }

    function onWheel(ev) {
        if (!root || root.hidden) {
            return;
        }
        if (!ev.ctrlKey && !ev.metaKey) {
            return;
        }
        ev.preventDefault();
        var delta = ev.deltaY > 0 ? 0.9 : 1.1;
        state.scale = clampScale(state.scale * delta);
        applyTransform();
    }

    function trapScroll() {
        var prevOverflow = document.body.style.overflow;
        document.body.dataset.ciPrevOverflow = prevOverflow || '';
        document.body.style.overflow = 'hidden';

        root._unlockScroll = function () {
            document.body.style.overflow =
                document.body.dataset.ciPrevOverflow || '';
            delete document.body.dataset.ciPrevOverflow;
        };
    }

    function releaseScroll() {
        if (typeof root._unlockScroll === 'function') {
            root._unlockScroll();
        }
    }

    function open(imageUrl, imageTitle) {
        ensureDom();
        resetZoom();
        img.onload = function () {
            resetZoom();
        };
        img.onerror = function () {
            if (titleEl) {
                titleEl.textContent = 'Could not load image';
            }
        };
        img.src = typeof imageUrl === 'string' ? imageUrl : '';
        titleEl.textContent = imageTitle || 'Document preview';
        root.hidden = false;
        trapScroll();
        requestAnimationFrame(applyTransform);
    }

    function close() {
        if (!root || root.hidden) {
            return;
        }
        root.hidden = true;
        img.removeAttribute('src');
        img.onload = null;
        img.onerror = null;
        resetZoom();
        releaseScroll();
    }

    window.openCiDocFullscreenZoom = open;
    window.closeCiDocFullscreenZoom = close;
})();
