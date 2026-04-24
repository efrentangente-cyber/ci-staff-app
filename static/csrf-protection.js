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

    function setHeader(headers, key, value) {
        if (!value) return headers;
        if (!headers) headers = {};
        if (headers instanceof Headers) {
            headers.set(key, value);
            return headers;
        }
        headers[key] = value;
        return headers;
    }

    function isSameOriginUrl(url) {
        if (!url) return true;
        if (typeof url !== 'string') return true;
        return !url.startsWith('http') || url.startsWith(window.location.origin);
    }
    
    // Add CSRF token to all fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Only add CSRF token to same-origin requests
        const isSameOrigin = isSameOriginUrl(url);
        const csrfToken = getCSRFToken(); // Always read latest token (session may rotate)

        if (isSameOrigin && csrfToken) {
            // Add CSRF token to POST, PUT, DELETE, PATCH requests
            const method = (options.method || 'GET').toUpperCase();
            if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
                options.headers = setHeader(options.headers, 'X-CSRFToken', csrfToken);
                options.headers = setHeader(options.headers, 'X-Requested-With', 'XMLHttpRequest');
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
        const isSameOrigin = isSameOriginUrl(this._url);
        const method = (this._method || 'GET').toUpperCase();
        const csrfToken = getCSRFToken(); // Always read latest token
        
        if (isSameOrigin && csrfToken && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            this.setRequestHeader('X-CSRFToken', csrfToken);
            this.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
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
                const latestToken = getCSRFToken();
                // Check if form already has CSRF token
                let existingToken = form.querySelector('input[name="csrf_token"]');

                if (!existingToken && latestToken) {
                    // Create hidden input for CSRF token
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'csrf_token';
                    input.value = latestToken;
                    form.appendChild(input);
                } else if (existingToken && latestToken) {
                    existingToken.value = latestToken;
                }
            }
        });

        // Always refresh CSRF input right before submit.
        document.addEventListener('submit', function(event) {
            const form = event.target;
            if (!form || form.tagName !== 'FORM') return;
            const method = (form.method || 'GET').toUpperCase();
            if (!['POST', 'PUT', 'DELETE'].includes(method)) return;
            const latestToken = getCSRFToken();
            if (!latestToken) return;
            let tokenInput = form.querySelector('input[name="csrf_token"]');
            if (!tokenInput) {
                tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'csrf_token';
                form.appendChild(tokenInput);
            }
            tokenInput.value = latestToken;
        }, true);
    });
    
    // Expose function to get CSRF token for manual use
    window.getCSRFToken = getCSRFToken;
    
})();
