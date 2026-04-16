/**
 * CI Location Tracker
 * Automatically captures GPS location every 30 seconds while CI form is open
 * Saves location to hidden form fields for submission with CI data
 */

let locationTrackingInterval = null;
let lastKnownLocation = { latitude: null, longitude: null };

function startLocationTracking() {
    console.log('Starting CI location tracking...');
    
    // Check if geolocation is supported
    if (!navigator.geolocation) {
        console.error('Geolocation is not supported by this browser');
        showLocationStatus('Geolocation not supported', 'danger');
        return;
    }
    
    // Get initial location immediately
    captureLocation();
    
    // Then capture every 30 seconds
    locationTrackingInterval = setInterval(captureLocation, 30000);
    
    showLocationStatus('Location tracking active', 'success');
}

function stopLocationTracking() {
    if (locationTrackingInterval) {
        clearInterval(locationTrackingInterval);
        locationTrackingInterval = null;
        console.log('Location tracking stopped');
        showLocationStatus('Location tracking stopped', 'info');
    }
}

function captureLocation() {
    navigator.geolocation.getCurrentPosition(
        function(position) {
            lastKnownLocation.latitude = position.coords.latitude;
            lastKnownLocation.longitude = position.coords.longitude;
            
            // Update hidden form fields
            const latField = document.getElementById('ci_latitude');
            const lngField = document.getElementById('ci_longitude');
            
            if (latField && lngField) {
                latField.value = lastKnownLocation.latitude;
                lngField.value = lastKnownLocation.longitude;
            }
            
            // Update status display
            const timestamp = new Date().toLocaleTimeString();
            showLocationStatus(`Location updated: ${timestamp}`, 'success');
            
            console.log(`Location captured: ${lastKnownLocation.latitude}, ${lastKnownLocation.longitude}`);
        },
        function(error) {
            let errorMessage = 'Location error: ';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage += 'Permission denied. Please enable location access.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage += 'Location unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage += 'Request timeout.';
                    break;
                default:
                    errorMessage += 'Unknown error.';
            }
            console.error(errorMessage);
            showLocationStatus(errorMessage, 'warning');
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

function showLocationStatus(message, type) {
    const statusDiv = document.getElementById('locationStatus');
    if (statusDiv) {
        statusDiv.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="font-size: 0.85rem; padding: 0.5rem 1rem;">
                <i class="bi bi-geo-alt-fill"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" style="font-size: 0.7rem;"></button>
            </div>
        `;
    }
}

// Auto-start tracking when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only start if we're on the CI application page
    if (document.getElementById('ci_latitude') && document.getElementById('ci_longitude')) {
        startLocationTracking();
        
        // Stop tracking when user leaves the page
        window.addEventListener('beforeunload', stopLocationTracking);
        
        // Also stop when form is submitted
        const form = document.getElementById('interview_form');
        if (form) {
            form.addEventListener('submit', stopLocationTracking);
        }
    }
});
