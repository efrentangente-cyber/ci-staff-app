// Autocomplete functionality for form fields
// Syncs with existing database records

class AutocompleteManager {
    constructor() {
        this.cache = {};
        this.activeField = null;
        this.suggestionBox = null;
        this.init();
    }

    init() {
        // Create suggestion box element
        this.createSuggestionBox();
        
        // Initialize autocomplete on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.setupAutocomplete();
        });
    }

    createSuggestionBox() {
        this.suggestionBox = document.createElement('div');
        this.suggestionBox.id = 'autocomplete-suggestions';
        this.suggestionBox.className = 'autocomplete-suggestions';
        this.suggestionBox.style.display = 'none';
        document.body.appendChild(this.suggestionBox);
    }

    setupAutocomplete() {
        // Fields to enable autocomplete
        const autocompleteFields = [
            { name: 'member_name', endpoint: '/api/autocomplete/names' },
            { name: 'member_contact', endpoint: '/api/autocomplete/contacts' },
            { name: 'member_address', endpoint: '/api/autocomplete/addresses' },
            { name: 'applicant_last_name', endpoint: '/api/autocomplete/last_names' },
            { name: 'applicant_first_name', endpoint: '/api/autocomplete/first_names' },
            { name: 'applicant_middle_name', endpoint: '/api/autocomplete/middle_names' },
            { name: 'spouse_last_name', endpoint: '/api/autocomplete/last_names' },
            { name: 'spouse_first_name', endpoint: '/api/autocomplete/first_names' },
            { name: 'spouse_middle_name', endpoint: '/api/autocomplete/middle_names' },
            { name: 'barangay', endpoint: '/api/autocomplete/barangays' },
            { name: 'municipality', endpoint: '/api/autocomplete/municipalities' },
            { name: 'province', endpoint: '/api/autocomplete/provinces' }
        ];

        autocompleteFields.forEach(field => {
            const inputs = document.querySelectorAll(`[name="${field.name}"], #${field.name}`);
            inputs.forEach(input => {
                this.attachAutocomplete(input, field.endpoint);
            });
        });
    }

    attachAutocomplete(input, endpoint) {
        if (!input) return;

        // Add autocomplete attribute
        input.setAttribute('autocomplete', 'off');
        input.classList.add('autocomplete-enabled');

        // Input event - fetch suggestions
        input.addEventListener('input', (e) => {
            this.handleInput(e.target, endpoint);
        });

        // Focus event - show cached suggestions
        input.addEventListener('focus', (e) => {
            if (e.target.value.length >= 2) {
                this.handleInput(e.target, endpoint);
            }
        });

        // Blur event - hide suggestions (with delay for click)
        input.addEventListener('blur', () => {
            setTimeout(() => this.hideSuggestions(), 200);
        });

        // Keyboard navigation
        input.addEventListener('keydown', (e) => {
            this.handleKeyboard(e);
        });
    }

    async handleInput(input, endpoint) {
        const query = input.value.trim();
        
        if (query.length < 2) {
            this.hideSuggestions();
            return;
        }

        this.activeField = input;

        // Check cache first
        const cacheKey = `${endpoint}:${query.toLowerCase()}`;
        if (this.cache[cacheKey]) {
            this.showSuggestions(this.cache[cacheKey], input);
            return;
        }

        // Fetch from server
        try {
            const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.success && data.suggestions) {
                // Cache results
                this.cache[cacheKey] = data.suggestions;
                this.showSuggestions(data.suggestions, input);
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
        }
    }

    showSuggestions(suggestions, input) {
        if (!suggestions || suggestions.length === 0) {
            this.hideSuggestions();
            return;
        }

        // Position suggestion box
        const rect = input.getBoundingClientRect();
        this.suggestionBox.style.top = `${rect.bottom + window.scrollY}px`;
        this.suggestionBox.style.left = `${rect.left + window.scrollX}px`;
        this.suggestionBox.style.width = `${rect.width}px`;

        // Build suggestion list
        this.suggestionBox.innerHTML = suggestions.map((suggestion, index) => `
            <div class="autocomplete-item" data-index="${index}" data-value="${this.escapeHtml(suggestion.value)}">
                <div class="suggestion-value">${this.highlightMatch(suggestion.value, input.value)}</div>
                ${suggestion.context ? `<div class="suggestion-context">${this.escapeHtml(suggestion.context)}</div>` : ''}
            </div>
        `).join('');

        // Add click handlers
        this.suggestionBox.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectSuggestion(item.dataset.value);
            });
        });

        this.suggestionBox.style.display = 'block';
    }

    hideSuggestions() {
        if (this.suggestionBox) {
            this.suggestionBox.style.display = 'none';
        }
    }

    selectSuggestion(value) {
        if (this.activeField) {
            this.activeField.value = value;
            
            // Trigger change event
            const event = new Event('change', { bubbles: true });
            this.activeField.dispatchEvent(event);
            
            // If selecting a name, try to auto-fill related fields
            if (this.activeField.name === 'member_name') {
                this.autoFillRelatedFields(value);
            }
        }
        this.hideSuggestions();
    }

    async autoFillRelatedFields(memberName) {
        try {
            const response = await fetch(`/api/autocomplete/member_details?name=${encodeURIComponent(memberName)}`);
            const data = await response.json();
            
            if (data.success && data.details) {
                // Auto-fill contact and address if fields exist and are empty
                const contactField = document.querySelector('[name="member_contact"]');
                const addressField = document.querySelector('[name="member_address"]');
                
                if (contactField && !contactField.value && data.details.contact) {
                    contactField.value = data.details.contact;
                    contactField.style.backgroundColor = '#f0fff4'; // Light green highlight
                    setTimeout(() => contactField.style.backgroundColor = '', 2000);
                }
                
                if (addressField && !addressField.value && data.details.address) {
                    addressField.value = data.details.address;
                    addressField.style.backgroundColor = '#f0fff4';
                    setTimeout(() => addressField.style.backgroundColor = '', 2000);
                }
            }
        } catch (error) {
            console.error('Auto-fill error:', error);
        }
    }

    handleKeyboard(e) {
        if (this.suggestionBox.style.display === 'none') return;

        const items = this.suggestionBox.querySelectorAll('.autocomplete-item');
        const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                this.setActiveItem(items, nextIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                this.setActiveItem(items, prevIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (currentIndex >= 0) {
                    this.selectSuggestion(items[currentIndex].dataset.value);
                }
                break;

            case 'Escape':
                this.hideSuggestions();
                break;
        }
    }

    setActiveItem(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('active');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('active');
            }
        });
    }

    highlightMatch(text, query) {
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return this.escapeHtml(text).replace(regex, '<strong>$1</strong>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeRegex(text) {
        return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}

// Initialize autocomplete manager
const autocompleteManager = new AutocompleteManager();

// Export for use in other scripts
window.AutocompleteManager = AutocompleteManager;
window.autocompleteManager = autocompleteManager;
