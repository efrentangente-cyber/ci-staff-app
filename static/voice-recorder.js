/* Voice Message Recorder */

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendVoiceMessage(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        updateRecordingUI(true);
    } catch (error) {
        alert('Microphone access denied. Please allow microphone access.');
    }
}

function stopVoiceRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        updateRecordingUI(false);
    }
}


function updateRecordingUI(recording) {
    const btn = document.getElementById('voiceBtn');
    const timer = document.getElementById('recordingTimer');
    
    if (recording) {
        btn.innerHTML = '<i class="bi bi-stop-circle-fill"></i>';
        btn.classList.add('recording');
        timer.style.display = 'block';
        startTimer();
    } else {
        btn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        btn.classList.remove('recording');
        timer.style.display = 'none';
        stopTimer();
    }
}

let timerInterval;
let seconds = 0;

function startTimer() {
    seconds = 0;
    timerInterval = setInterval(() => {
        seconds++;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        document.getElementById('recordingTimer').textContent = 
            `${mins}:${secs.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    seconds = 0;
}

async function sendVoiceMessage(audioBlob) {
    const formData = new FormData();
    formData.append('voice', audioBlob, 'voice-message.webm');
    formData.append('app_id', APP_ID);
    
    try {
        const response = await fetch('/send_voice_message', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            location.reload();
        }
    } catch (error) {
        console.error('Error sending voice message:', error);
    }
}
