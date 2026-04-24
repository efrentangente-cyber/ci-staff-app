// SMS Modal for Loan Decisions
// Shows SMS templates when approving/disapproving/deferring applications

let currentAppId = null;
let currentAction = null;
let currentMemberName = '';
let currentLoanAmount = '';
let currentLoanType = '';
let currentTemplateId = null;

// Show SMS modal
function showSMSModal(appId, action, memberName, loanAmount, loanType, memberContact) {
    currentAppId = appId;
    currentAction = action;
    currentMemberName = memberName;
    currentLoanAmount = loanAmount;
    currentLoanType = loanType;
    currentTemplateId = null;
    
    // Set modal title and color
    const modal = document.getElementById('smsModal');
    const modalTitle = modal.querySelector('.modal-title');
    const modalHeader = modal.querySelector('.modal-header');
    const sendBtn = document.getElementById('send_sms_btn');
    
    // Update title, color, and button based on action
    if (action === 'approved') {
        modalTitle.innerHTML = '<i class="bi bi-check-circle"></i> Approve & Send SMS';
        modalHeader.className = 'modal-header bg-success text-white';
        sendBtn.className = 'btn btn-success';
        sendBtn.innerHTML = '<i class="bi bi-send"></i> Send SMS & Approve';
    } else if (action === 'disapproved') {
        modalTitle.innerHTML = '<i class="bi bi-x-circle"></i> Disapprove & Send SMS';
        modalHeader.className = 'modal-header bg-danger text-white';
        sendBtn.className = 'btn btn-danger';
        sendBtn.innerHTML = '<i class="bi bi-send"></i> Send SMS & Disapprove';
    } else if (action === 'deferred') {
        modalTitle.innerHTML = '<i class="bi bi-clock"></i> Defer & Send SMS';
        modalHeader.className = 'modal-header bg-warning text-white';
        sendBtn.className = 'btn btn-warning';
        sendBtn.innerHTML = '<i class="bi bi-send"></i> Send SMS & Defer';
    }
    
    // Update member info display
    document.getElementById('sms_member_name').textContent = memberName;
    document.getElementById('sms_member_contact').textContent = memberContact;
    document.getElementById('sms_loan_amount').textContent = '₱' + parseFloat(loanAmount).toLocaleString();
    document.getElementById('sms_loan_type').textContent = loanType;
    
    // Clear previous message and notes
    document.getElementById('sms_message').value = '';
    document.getElementById('sms_notes').value = '';
    updateCharCount();
    
    // Load templates for this action
    loadSMSTemplates(action);
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Load SMS templates by category
function loadSMSTemplates(category) {
    fetch(`/api/get_sms_templates/${category}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayTemplates(data.templates);
            } else {
                console.error('Failed to load templates');
            }
        })
        .catch(error => {
            console.error('Error loading templates:', error);
        });
}

// Display templates in modal
function displayTemplates(templates) {
    const container = document.getElementById('sms_templates_list');
    
    if (templates.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> No templates available for this action. 
                <a href="/manage_sms_templates" target="_blank">Create templates</a> or write a custom message below.
            </div>
        `;
        return;
    }
    
    container.innerHTML = templates.map(template => `
        <div class="template-option" onclick="selectTemplate(${template.id}, \`${escapeHtml(template.message)}\`)">
            <div class="template-name">
                <i class="bi bi-chat-square-text"></i> ${escapeHtml(template.name)}
            </div>
            <div class="template-preview">
                ${fillTemplateVariables(template.message)}
            </div>
        </div>
    `).join('');
}

// Select a template
function selectTemplate(templateId, message) {
    currentTemplateId = templateId;
    // Remove active class from all templates
    document.querySelectorAll('.template-option').forEach(el => {
        el.classList.remove('active');
    });
    
    // Add active class to selected template
    event.currentTarget.classList.add('active');
    
    // Fill message textarea with template
    const filledMessage = fillTemplateVariables(message);
    document.getElementById('sms_message').value = filledMessage;
    
    // Update character count
    updateCharCount();
}

// Fill template variables with actual data
function fillTemplateVariables(message) {
    const today = new Date().toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    return message
        .replace(/{member_name}/g, currentMemberName)
        .replace(/{loan_amount}/g, parseFloat(currentLoanAmount).toLocaleString())
        .replace(/{loan_type}/g, currentLoanType)
        .replace(/{date}/g, today);
}

// Update character count
function updateCharCount() {
    const message = document.getElementById('sms_message').value;
    const count = message.length;
    const counter = document.getElementById('sms_char_count');
    
    counter.textContent = `${count} / 160 characters`;
    
    if (count > 160) {
        counter.classList.remove('bg-secondary');
        counter.classList.add('bg-warning');
    } else {
        counter.classList.remove('bg-warning');
        counter.classList.add('bg-secondary');
    }
}

// Send SMS and update status
function sendSMSAndUpdate() {
    const message = document.getElementById('sms_message').value.trim();
    const notes = document.getElementById('sms_notes').value.trim();
    
    if (!message) {
        alert('Please enter an SMS message or select a template');
        return;
    }
    
    // Disable button to prevent double-click
    const btn = document.getElementById('send_sms_btn');
    const originalBtnText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving & sending SMS…';
    
    const controller = new AbortController();
    const timeoutMs = 60000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    // Send request (server no longer blocks on Socket.IO; still guard against network hangs)
    fetch(`/send_sms_and_update_status/${currentAppId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        signal: controller.signal,
        body: JSON.stringify({
            action: currentAction,
            message: message,
            notes: notes,
            template_id: currentTemplateId
        })
    })
    .then(async (response) => {
        let data;
        const text = await response.text();
        try {
            data = text ? JSON.parse(text) : {};
        } catch (parseErr) {
            throw new Error(response.status >= 500
                ? 'Server error. Try again in a moment.'
                : 'Unexpected response. Please try again.');
        }
        if (!response.ok) {
            throw new Error((data && data.error) || `Request failed (${response.status})`);
        }
        return data;
    })
    .then((data) => {
        if (data.success) {
            if (data.sms_error) {
                showNotification('warning', (data.message || 'Decision saved.') + ' ' + (data.sms_error || ''));
            } else {
                showNotification('success', data.message || 'Decision saved. SMS was sent to the member.');
            }
            const modal = bootstrap.Modal.getInstance(document.getElementById('smsModal'));
            if (modal) modal.hide();
            setTimeout(() => {
                location.reload();
            }, 800);
        } else {
            throw new Error(data.error || 'Failed to save');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        const msg = (error && error.name === 'AbortError')
            ? 'Request timed out. Check your connection and try again.'
            : (error.message || 'Request failed');
        showNotification('error', msg);
        btn.disabled = false;
        btn.innerHTML = originalBtnText;
    })
    .finally(() => {
        clearTimeout(timeoutId);
    });
}

// Helper functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function showNotification(type, message) {
    const classMap = { success: 'alert-success', error: 'alert-danger', warning: 'alert-warning' };
    const alertClass = classMap[type] || 'alert-info';
    const icon = type === 'success' ? 'check-circle' : 'exclamation-triangle';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show`;
    notification.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <i class="bi bi-${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Initialize character counter
document.addEventListener('DOMContentLoaded', function() {
    const messageTextarea = document.getElementById('sms_message');
    if (messageTextarea) {
        messageTextarea.addEventListener('input', updateCharCount);
    }
});
