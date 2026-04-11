/* ============================================
   PROFESSIONAL INTERACTIONS & ANIMATIONS
   Smooth, Modern, Enterprise-Grade
   ============================================ */

(function() {
    'use strict';

    // ============================================
    // PAGE LOAD ANIMATIONS
    // ============================================
    document.addEventListener('DOMContentLoaded', function() {
        // Animate cards on page load
        animateOnLoad();
        
        // Add ripple effect to buttons
        addRippleEffect();
        
        // Animate numbers
        animateNumbers();
        
        // Add smooth scroll
        addSmoothScroll();
        
        // Enhance tables
        enhanceTables();
        
        // Add loading states
        addLoadingStates();
    });

    // ============================================
    // ANIMATE ELEMENTS ON LOAD
    // ============================================
    function animateOnLoad() {
        // Animate cards
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
            card.classList.add('animate-fade-in-up');
            card.style.animationDelay = `${index * 0.1}s`;
        });

        // Animate stat cards
        const statCards = document.querySelectorAll('.stat-card');
        statCards.forEach((card, index) => {
            card.classList.add('animate-scale-in');
            card.style.animationDelay = `${index * 0.15}s`;
        });

        // Animate table rows
        const tableRows = document.querySelectorAll('tbody tr');
        tableRows.forEach((row, index) => {
            if (index < 10) { // Only first 10 rows
                row.classList.add('animate-fade-in');
                row.style.animationDelay = `${index * 0.05}s`;
            }
        });
    }

    // ============================================
    // RIPPLE EFFECT FOR BUTTONS
    // ============================================
    function addRippleEffect() {
        const buttons = document.querySelectorAll('.btn');
        
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                ripple.classList.add('ripple-effect');
                
                this.appendChild(ripple);
                
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    // ============================================
    // ANIMATE NUMBERS (COUNT UP)
    // ============================================
    function animateNumbers() {
        const numbers = document.querySelectorAll('.stat-number, .count-up');
        
        numbers.forEach(element => {
            const target = parseInt(element.textContent.replace(/,/g, ''));
            if (isNaN(target)) return;
            
            const duration = 1500;
            const increment = target / (duration / 16);
            let current = 0;
            
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    element.textContent = target.toLocaleString();
                    clearInterval(timer);
                } else {
                    element.textContent = Math.floor(current).toLocaleString();
                }
            }, 16);
        });
    }

    // ============================================
    // SMOOTH SCROLL
    // ============================================
    function addSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ============================================
    // ENHANCE TABLES
    // ============================================
    function enhanceTables() {
        const tables = document.querySelectorAll('table');
        
        tables.forEach(table => {
            // Add hover class
            table.classList.add('table-hover');
            
            // Highlight row on click
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.addEventListener('click', function() {
                    rows.forEach(r => r.classList.remove('table-active'));
                    this.classList.add('table-active');
                });
            });
        });
    }

    // ============================================
    // LOADING STATES
    // ============================================
    function addLoadingStates() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = this.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    const originalText = submitBtn.innerHTML;
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
                    
                    // Re-enable after 5 seconds as fallback
                    setTimeout(() => {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }, 5000);
                }
            });
        });
    }

    // ============================================
    // TOAST NOTIFICATIONS
    // ============================================
    window.showToast = function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} notification-enter`;
        toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    // ============================================
    // CONFIRM DIALOGS
    // ============================================
    window.confirmAction = function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    };

    // ============================================
    // INTERSECTION OBSERVER (Animate on scroll)
    // ============================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements with .observe-me class
    document.querySelectorAll('.observe-me').forEach(el => {
        observer.observe(el);
    });

    // ============================================
    // BADGE ANIMATION ON UPDATE
    // ============================================
    window.animateBadge = function(badgeElement) {
        badgeElement.classList.add('badge-bounce');
        setTimeout(() => {
            badgeElement.classList.remove('badge-bounce');
        }, 500);
    };

    // ============================================
    // CARD LOADING STATE
    // ============================================
    window.showCardLoading = function(cardElement) {
        const overlay = document.createElement('div');
        overlay.className = 'card-loading-overlay';
        overlay.innerHTML = '<div class="spinner-border text-primary"></div>';
        overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
            border-radius: inherit;
        `;
        cardElement.style.position = 'relative';
        cardElement.appendChild(overlay);
    };

    window.hideCardLoading = function(cardElement) {
        const overlay = cardElement.querySelector('.card-loading-overlay');
        if (overlay) overlay.remove();
    };

    // ============================================
    // AUTO-HIDE ALERTS
    // ============================================
    document.querySelectorAll('.alert').forEach(alert => {
        if (!alert.classList.contains('alert-permanent')) {
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-20px)';
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        }
    });

    // ============================================
    // ENHANCE SEARCH INPUTS
    // ============================================
    document.querySelectorAll('input[type="search"], input[placeholder*="Search"]').forEach(input => {
        const wrapper = document.createElement('div');
        wrapper.className = 'search-wrapper position-relative';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        
        const icon = document.createElement('i');
        icon.className = 'bi bi-search';
        wrapper.insertBefore(icon, input);
    });

    // ============================================
    // COPY TO CLIPBOARD
    // ============================================
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard!', 'success');
        }).catch(() => {
            showToast('Failed to copy', 'danger');
        });
    };

    // ============================================
    // PRINT FUNCTIONALITY
    // ============================================
    window.printElement = function(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const printWindow = window.open('', '', 'height=600,width=800');
        printWindow.document.write('<html><head><title>Print</title>');
        printWindow.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">');
        printWindow.document.write('</head><body>');
        printWindow.document.write(element.innerHTML);
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.print();
    };

})();
