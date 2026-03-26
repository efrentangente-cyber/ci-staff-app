// CSRF Protection - Automatically add CSRF tokens to all AJAX requests
(function() {
    'use strict';
    
    // Get CSRF token from meta tag or cookie
    function getCSRFToken() {
        // Try to get from meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return decodeURIComponent(value);
            }
        }
        
        return null;
    }
    
    // Store CSRF token
    const csrfToken = getCSRFToken();
    
    // Add CSRF token to all fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Only add CSRF token to same-origin requests
        const isSameOrigin = !url.startsWith('http') || url.startsWith(window.location.origin);
        
        if (isSameOrigin && csrfToken) {
            // Add CSRF token to POST, PUT, DELETE, PATCH requests
            const method = (options.method || 'GET').toUpperCase();
            if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
                options.headers = options.headers || {};
                
                // If headers is a Headers object, use set method
                if (options.headers instanceof Headers) {
                    options.headers.set('X-CSRFToken', csrfToken);
                } else {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
        }
        
        return originalFetch(url, options);
    };
    
    // Add CSRF token to all XMLHttpRequest requests
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        this._method = method;
        this._url = url;
        return originalOpen.call(this, method, url, ...args);
    };
    
    XMLHttpRequest.prototype.send = function(...args) {
        const isSameOrigin = !this._url.startsWith('http') || this._url.startsWith(window.location.origin);
        const method = (this._method || 'GET').toUpperCase();
        
        if (isSameOrigin && csrfToken && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            this.setRequestHeader('X-CSRFToken', csrfToken);
        }
        
        return originalSend.apply(this, args);
    };
    
    // Add CSRF token to all forms on submit
    document.addEventListener('DOMContentLoaded', function() {
        // Add CSRF token to all forms that don't have it
        const forms = document.querySelectorAll('form');
        forms.forEach(function(form) {
            const method = (form.method || 'GET').toUpperCase();
            
            // Only add to POST, PUT, DELETE forms
            if (['POST', 'PUT', 'DELETE'].includes(method)) {
                // Check if form already has CSRF token
                const existingToken = form.querySelector('input[name="csrf_token"]');
                
                if (!existingToken && csrfToken) {
                    // Create hidden input for CSRF token
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'csrf_token';
                    input.value = csrfToken;
                    form.appendChild(input);
                }
            }
        });
    });
    
    // Expose function to get CSRF token for manual use
    window.getCSRFToken = getCSRFToken;
    
})();
