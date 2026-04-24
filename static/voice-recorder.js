/* Voice-to-text for chat input */

let isRecording = false;
let recognition = null;
let dictationBase = '';
let dictationFinal = '';

function updateRecordingUI(recording) {
    const btn = document.getElementById('voiceBtn');
    const indicator = document.getElementById('recordingTimer');
    if (!btn || !indicator) return;

    if (recording) {
        btn.innerHTML = '<i class="bi bi-stop-circle-fill"></i>';
        btn.classList.add('recording');
        indicator.textContent = 'Listening…';
        indicator.style.display = 'inline-block';
    } else {
        btn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        btn.classList.remove('recording');
        indicator.style.display = 'none';
    }
}

async function startVoiceRecording() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        alert('Voice-to-text is not supported in this browser.');
        return;
    }
    const input = document.getElementById('messageInput');
    if (!input) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'en-US';
    dictationBase = (input.value || '').trim();
    dictationFinal = '';

    recognition.onresult = function (event) {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const t = (event.results[i][0] && event.results[i][0].transcript) || '';
            if (event.results[i].isFinal) {
                dictationFinal += t + ' ';
            } else {
                interim += t;
            }
        }
        const merged = (dictationFinal + interim).trim();
        input.value = dictationBase ? `${dictationBase} ${merged}`.trim() : merged;
    };

    recognition.onerror = function (event) {
        if (event.error === 'not-allowed') {
            alert('Microphone access denied. Please allow microphone access.');
        } else if (event.error !== 'aborted' && event.error !== 'no-speech') {
            alert('Voice input failed: ' + event.error);
        }
        stopVoiceRecording();
    };

    recognition.onend = function () {
        stopVoiceRecording();
    };

    try {
        recognition.start();
        isRecording = true;
        updateRecordingUI(true);
    } catch (e) {
        alert('Could not start voice input. Try again.');
        stopVoiceRecording();
    }
}

function stopVoiceRecording() {
    if (recognition && isRecording) {
        try { recognition.stop(); } catch (_) {}
    }
    isRecording = false;
    updateRecordingUI(false);
}
