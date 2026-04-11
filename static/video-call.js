/* Video/Voice Call System using Jitsi Meet */

let jitsiAPI = null;

function startVideoCall(roomName, userName) {
    const domain = 'meet.jit.si';
    const options = {
        roomName: `dccco_${roomName}`,
        width: '100%',
        height: '100%',
        parentNode: document.querySelector('#jitsiContainer'),
        userInfo: {
            displayName: userName
        },
        configOverwrite: {
            startWithAudioMuted: false,
            startWithVideoMuted: false,
            enableWelcomePage: false
        },
        interfaceConfigOverwrite: {
            TOOLBAR_BUTTONS: [
                'microphone', 'camera', 'closedcaptions', 'desktop',
                'fullscreen', 'fodeviceselection', 'hangup',
                'chat', 'recording', 'settings', 'videoquality',
                'filmstrip', 'stats', 'shortcuts', 'tileview'
            ],
            SHOW_JITSI_WATERMARK: false,
            SHOW_WATERMARK_FOR_GUESTS: false
        }
    };
    
    jitsiAPI = new JitsiMeetExternalAPI(domain, options);
    
    document.getElementById('callModal').style.display = 'flex';
    
    jitsiAPI.addEventListener('videoConferenceLeft', () => {
        endCall();
    });
}


function startVoiceCall(roomName, userName) {
    const domain = 'meet.jit.si';
    const options = {
        roomName: `dccco_voice_${roomName}`,
        width: '100%',
        height: '100%',
        parentNode: document.querySelector('#jitsiContainer'),
        userInfo: {
            displayName: userName
        },
        configOverwrite: {
            startWithAudioMuted: false,
            startWithVideoMuted: true,
            enableWelcomePage: false
        }
    };
    
    jitsiAPI = new JitsiMeetExternalAPI(domain, options);
    document.getElementById('callModal').style.display = 'flex';
    
    jitsiAPI.addEventListener('videoConferenceLeft', () => {
        endCall();
    });
}

function endCall() {
    if (jitsiAPI) {
        jitsiAPI.dispose();
        jitsiAPI = null;
    }
    document.getElementById('callModal').style.display = 'none';
}
