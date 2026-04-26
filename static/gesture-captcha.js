/**
 * Sign-up gesture captcha: webcam + MediaPipe Hands → classify pose and match
 * server target { wave, thumbs, peace, ok, fist }.
 */
(function () {
    'use strict';

    // Minimal skeleton for overlay (if drawing_utils has no HAND_CONNECTIONS)
    const HAND_SKELETON = [
        [0, 1], [1, 2], [2, 3], [3, 4],
        [0, 5], [5, 6], [6, 7], [7, 8],
        [0, 9], [9, 10], [10, 11], [11, 12],
        [0, 13], [13, 14], [14, 15], [15, 16],
        [0, 17], [17, 18], [18, 19], [19, 20],
        [5, 9], [9, 13], [13, 17]
    ];

    function euclid2(a, b) {
        if (!a || !b) return 0;
        return Math.hypot(a.x - b.x, a.y - b.y);
    }

    function classifyHandGesture(lm) {
        if (!lm || lm.length < 21) return 'unknown';
        const w = 0;
        const handSize = euclid2(lm[0], lm[9]) || 0.0001;

        function fingerExt(tip, pip) {
            return euclid2(lm[tip], lm[w]) > euclid2(lm[pip], lm[w]) * 1.05;
        }

        const idxE = fingerExt(8, 6);
        const midE = fingerExt(12, 10);
        const ringE = fingerExt(16, 14);
        const pinE = fingerExt(20, 18);
        const thumbUp = (lm[4].y < lm[3].y) && (lm[4].y < lm[2].y);
        const pinch = euclid2(lm[4], lm[8]) / handSize;

        if (idxE && midE && !ringE && !pinE) {
            return 'peace';
        }
        if (idxE && midE && ringE && pinE) {
            return 'wave';
        }
        if (pinch < 0.16) {
            return 'ok';
        }
        if (!idxE && !midE && !ringE && !pinE) {
            if (thumbUp) {
                return 'thumbs';
            }
            return 'fist';
        }
        if (idxE && midE && ringE && !pinE) {
            return 'unknown';
        }
        return 'unknown';
    }

    function initGestureCaptcha(root) {
        if (!root) return;
        const expectedId = (root.getAttribute('data-expected-id') || '').trim();
        const promptHint = (root.getAttribute('data-prompt-hint') || '').trim();
        const hidden = document.getElementById('hand_sign');
        const errEl = document.getElementById('handSignError');
        const statusEl = document.getElementById('gcStatus');
        const video = document.getElementById('gcVideo');
        const canvas = document.getElementById('gcCanvas');
        const btnStart = document.getElementById('gcStart');
        const btnStop = document.getElementById('gcStop');
        const btnVerify = document.getElementById('gcVerify');
        const fallback = document.getElementById('gcFallback');
        const btnToggleFallback = document.getElementById('gcShowFallback');
        const matchedBox = document.getElementById('gcMatched');

        var hands = null;
        var camera = null;
        var lastResult = null;
        var verifyTimer = null;
        var matched = false;

        function setStatus(msg, isErr) {
            if (statusEl) {
                statusEl.textContent = msg;
                statusEl.classList.toggle('text-danger', !!isErr);
                statusEl.classList.toggle('text-success', !isErr && (msg.indexOf('✓') >= 0 || /verified|continue/i.test(msg)));
            }
        }

        function showFallbackMode() {
            if (fallback) { fallback.classList.remove('d-none'); }
            if (btnStart) { btnStart.classList.add('d-none'); }
            if (btnStop) { btnStop.classList.add('d-none'); }
            if (btnVerify) { btnVerify.classList.add('d-none'); }
            if (previewWrap) { previewWrap.classList.add('d-none'); }
        }

        function onMatched() {
            matched = true;
            if (verifyTimer) {
                clearInterval(verifyTimer);
                verifyTimer = null;
            }
            if (hidden) { hidden.value = expectedId; }
            if (errEl) { errEl.classList.add('d-none'); }
            if (matchedBox) { matchedBox.classList.remove('d-none'); }
            setStatus('✓ Gesture verified. You can tap Register below.', false);
            if (camera) {
                try { camera.stop(); } catch (e) { /* */ }
            }
        }

        function drawHandOverlay() {
            if (!canvas || !video || !lastResult) return;
            const ctx = canvas.getContext('2d');
            const vw = video.videoWidth;
            const vh = video.videoHeight;
            if (!vw || !vh) return;
            canvas.width = vw;
            canvas.height = vh;
            ctx.clearRect(0, 0, vw, vh);
            if (!lastResult.multiHandLandmarks || !lastResult.multiHandLandmarks[0]) return;
            const lm = lastResult.multiHandLandmarks[0];
            ctx.strokeStyle = 'rgba(0, 200, 83, 0.85)';
            ctx.lineWidth = 2.5;
            ctx.lineCap = 'round';
            for (var s = 0; s < HAND_SKELETON.length; s++) {
                const a = HAND_SKELETON[s];
                const p0 = lm[a[0]];
                const p1 = lm[a[1]];
                ctx.beginPath();
                ctx.moveTo(p0.x * vw, p0.y * vh);
                ctx.lineTo(p1.x * vw, p1.y * vh);
                ctx.stroke();
            }
            ctx.fillStyle = 'rgba(255, 200, 0, 0.9)';
            for (var i = 0; i < lm.length; i++) {
                const p = lm[i];
                ctx.beginPath();
                ctx.arc(p.x * vw, p.y * vh, 2.2, 0, 2 * Math.PI);
                ctx.fill();
            }
        }

        function onResults(results) {
            lastResult = results;
            drawHandOverlay();
        }

        function loadScripts(next) {
            if (window.Hands && window.Camera) {
                next();
                return;
            }
            const list = [
                'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js',
                'https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js',
                'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469404/hands.js'
            ];
            var u = 0;
            (function go() {
                if (u >= list.length) { next(); return; }
                var s = document.createElement('script');
                s.src = list[u];
                s.async = true;
                s.crossOrigin = 'anonymous';
                s.onload = function () { u += 1; go(); };
                s.onerror = function () {
                    setStatus('Could not load hand detection. Use “Can’t use camera?” below.', true);
                    showFallbackMode();
                };
                document.head.appendChild(s);
            })();
        }

        function startCamera() {
            if (!video) return;
            setStatus('Starting camera and hand model…', false);
            loadScripts(function () {
                if (typeof window.Hands !== 'function' || typeof window.Camera !== 'function') {
                    setStatus('Hand detection is unavailable. Use emoji option below.', true);
                    showFallbackMode();
                    return;
                }
                try {
                    if (camera) { try { camera.stop(); } catch (e) { /* */ } }
                    if (hands) { try { if (typeof hands.close === 'function') { hands.close(); } } catch (e) { /* */ } }

                    hands = new window.Hands({
                        locateFile: function (f) {
                            return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469404/' + f;
                        }
                    });
                    hands.setOptions({
                        maxNumHands: 1,
                        modelComplexity: 1,
                        minDetectionConfidence: 0.55,
                        minTrackingConfidence: 0.5
                    });
                    hands.onResults(onResults);
                    camera = new window.Camera(video, {
                        onFrame: async function () {
                            if (hands) { await hands.send({ image: video }); }
                        },
                        width: 640,
                        height: 480
                    });
                    camera.start();
                    if (btnVerify) { btnVerify.disabled = false; }
                    if (btnStop) { btnStop.disabled = false; }
                    setStatus('Match the target above, then tap “Verify gesture.”', false);
                } catch (e) {
                    setStatus('Camera or detection failed. Use emoji option below.', true);
                    showFallbackMode();
                }
            });
        }

        function stopCamera() {
            if (verifyTimer) {
                clearInterval(verifyTimer);
                verifyTimer = null;
            }
            if (camera) { try { camera.stop(); } catch (e) { /* */ } }
            if (video && video.srcObject) {
                try {
                    video.srcObject.getTracks().forEach(function (t) { t.stop(); });
                } catch (e) { /* */ }
                video.srcObject = null;
            }
        }

        function verifyGesture() {
            if (matched) return;
            if (!lastResult || !lastResult.multiHandLandmarks || !lastResult.multiHandLandmarks[0]) {
                setStatus('We don’t see a hand. Face the camera, add light, and try again.', true);
                return;
            }
            if (btnVerify) { btnVerify.disabled = true; }
            setStatus('Hold still for a second…', false);
            var good = 0;
            var n = 0;
            const maxN = 20;
            const need = 10;
            verifyTimer = setInterval(function () {
                if (matched) {
                    clearInterval(verifyTimer);
                    return;
                }
                n += 1;
                if (lastResult && lastResult.multiHandLandmarks && lastResult.multiHandLandmarks[0]) {
                    const g = classifyHandGesture(lastResult.multiHandLandmarks[0]);
                    if (g === expectedId) { good += 1; }
                }
                if (n >= maxN) {
                    clearInterval(verifyTimer);
                    verifyTimer = null;
                    if (btnVerify) { btnVerify.disabled = false; }
                    if (good >= need) {
                        onMatched();
                    } else {
                        setStatus('We didn’t get a stable match. Try: ' + (promptHint || 'copy the hand pose in the target') + ' — then Verify again.', true);
                    }
                }
            }, 50);
        }

        if (btnStart) { btnStart.addEventListener('click', startCamera); }
        if (btnStop) { btnStop.addEventListener('click', function () { stopCamera(); setStatus('Camera stopped. Tap Start to try again.', false); }); }
        if (btnVerify) { btnVerify.addEventListener('click', verifyGesture); }
        if (btnToggleFallback) {
            btnToggleFallback.addEventListener('click', function () {
                showFallbackMode();
                setStatus('Tap the matching emoji, then continue.', false);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initGestureCaptcha(document.getElementById('gestureRoot'));
        });
    } else {
        initGestureCaptcha(document.getElementById('gestureRoot'));
    }
}());
