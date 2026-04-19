// Real-time Dashboard Updates with WebSocket Push
// Instant updates when new applications are submitted

let lastUpdateTime = Date.now();
let currentDashboard = null;

// Detect which dashboard we're on
if (window.location.pathname.includes('/admin/dashboard')) {
    currentDashboard = 'admin';
} else if (window.location.pathname.includes('/loan/dashboard')) {
    currentDashboard = 'loan';
} else if (window.location.pathname.includes('/ci/dashboard')) {
    currentDashboard = 'ci';
}

// WebSocket connection for instant updates
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 100,  // Immediate reconnection
    reconnectionAttempts: Infinity,  // Never stop trying
    timeout: 5000,
    upgrade: true,
    rememberUpgrade: true,
    forceNew: false
});

// Connection status logging
socket.on('connect', function() {
    console.log('✅ Dashboard Socket.IO connected - Real-time updates enabled');
    console.log('🔄 Fetching latest data...');
    refreshApplications(); // Immediately fetch latest data on connect
});

socket.on('disconnect', function(reason) {
    console.log('❌ Dashboard Socket.IO disconnected:', reason);
    if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        socket.connect();
    }
});

socket.on('connect_error', function(error) {
    console.log('⚠️ Connection error:', error);
});

socket.on('reconnect', function(attemptNumber) {
    console.log('🔄 Reconnected after', attemptNumber, 'attempts');
    refreshApplications(); // Fetch latest data after reconnection
});

// Listen for new application submissions - INSTANT UPDATE
socket.on('new_application', function(data) {
    console.log('🆕 NEW APPLICATION:', data);
    // Show toast notification
    showToast('New Application', `${data.member_name} submitted a loan application`, 'success');
    // Immediately refresh the table
    refreshApplications();
});

// Listen for application updates - INSTANT UPDATE
socket.on('application_updated', function(data) {
    console.log('🔄 APPLICATION UPDATED:', data);
    // Show toast notification
    const statusText = data.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    showToast('Application Updated', `${data.member_name} - ${statusText}`, 'info');
    // Immediately refresh the table
    refreshApplications();
});

// Toast notification function
function showToast(title, message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : type === 'info' ? 'info' : 'warning'} alert-dismissible fade show`;
    toast.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML = `
        <strong>${title}</strong><br>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function refreshApplications() {
    if (!currentDashboard) return;
    
    const apiUrl = `/api/${currentDashboard}/applications`;
    
    fetch(apiUrl)
        .then(response => response.json())
        .then(applications => {
            updateApplicationsTable(applications);
            lastUpdateTime = Date.now();
        })
        .catch(error => console.error('Error fetching applications:', error));
}

function updateApplicationsTable(applications) {
    const tbody = document.querySelector('#applicationsTable tbody');
    if (!tbody) return;
    
    // Store current search and filter values
    const searchInput = document.getElementById('searchInput');
    const filterSelect = document.getElementById('statusFilter');
    const searchValue = searchInput ? searchInput.value : '';
    const filterValue = filterSelect ? filterSelect.value : 'all';
    
    tbody.innerHTML = '';
    
    applications.forEach(app => {
        const row = document.createElement('tr');
        
        // Format date (DD-MM-YY)
        const date = app.submitted_at.substring(8, 10) + '-' + 
                     app.submitted_at.substring(5, 7) + '-' + 
                     app.submitted_at.substring(2, 4);
        
        // Status badge color
        let badgeClass = 'warning';
        if (app.status === 'approved') badgeClass = 'success';
        else if (app.status === 'disapproved') badgeClass = 'danger';
        else if (app.status === 'ci_completed') badgeClass = 'info';
        
        // Build row based on dashboard type
        if (currentDashboard === 'admin') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td><strong>₱${parseFloat(app.loan_amount).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${app.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                </td>
                <td>${app.loan_staff_name || 'N/A'}</td>
                <td>${app.ci_staff_name || 'N/A'}</td>
                <td>${date}</td>
                <td>
                    <a href="/admin/application/${app.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i>
                        <span class="btn-text">Review</span>
                    </a>
                </td>
            `;
        } else if (currentDashboard === 'loan') {
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td><strong>₱${parseFloat(app.loan_amount).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                <td>
                    <span class="badge bg-${badgeClass}">
                        ${app.status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                </td>
                <td>${app.ci_staff_name || 'N/A'}</td>
                <td>
                    <a href="/loan/application/${app.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i>
                        <span class="btn-text">View</span>
                    </a>
                </td>
            `;
        } else if (currentDashboard === 'ci') {
            const actionButton = app.status === 'ci_completed' 
                ? `<a href="/ci/application/${app.id}" class="btn btn-sm btn-success">
                       <i class="bi bi-eye"></i>
                       <span class="btn-text">View</span>
                   </a>`
                : `<a href="/ci/application/${app.id}" class="btn btn-sm btn-primary">
                       <i class="bi bi-pencil"></i>
                       <span class="btn-text">Start</span>
                   </a>`;
            
            row.innerHTML = `
                <td><strong>#${app.id}</strong> ${app.member_name}</td>
                <td>${date}</td>
                <td>${app.member_address || 'N/A'}</td>
                <td>${actionButton}</td>
            `;
        }
        
        tbody.appendChild(row);
    });
    
    // Update stats if they exist
    updateDashboardStats(applications);
    
    // Reapply search and filter
    if (searchValue && typeof searchApplications === 'function') {
        searchInput.value = searchValue;
        searchApplications();
    }
    if (filterValue !== 'all' && typeof filterApplications === 'function') {
        filterSelect.value = filterValue;
        filterApplications();
    } else {
        const totalCount = document.getElementById('totalCount');
        if (totalCount) {
            totalCount.textContent = `${applications.length} Total`;
        }
    }
}

function updateDashboardStats(applications) {
    // Update stats based on dashboard type
    if (currentDashboard === 'admin') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const forReview = applications.filter(a => ['submitted', 'ci_completed'].includes(a.status)).length;
        const forReviewStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (forReviewStat) forReviewStat.textContent = forReview;
        
        const approved = applications.filter(a => a.status === 'approved').length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;
    } else if (currentDashboard === 'loan') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const pending = applications.filter(a => a.status === 'submitted').length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;
        
        const approved = applications.filter(a => a.status === 'approved').length;
        const approvedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (approvedStat) approvedStat.textContent = approved;
        
        const totalAmount = applications.reduce((sum, a) => sum + parseFloat(a.loan_amount || 0), 0);
        const amountStat = document.querySelectorAll('.stat-card')[3]?.querySelector('h3');
        if (amountStat) amountStat.textContent = '₱' + totalAmount.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
    } else if (currentDashboard === 'ci') {
        const totalStat = document.querySelector('.stat-card.blue h3');
        if (totalStat) totalStat.textContent = applications.length;
        
        const pending = applications.filter(a => a.status !== 'ci_completed').length;
        const pendingStat = document.querySelectorAll('.stat-card')[1]?.querySelector('h3');
        if (pendingStat) pendingStat.textContent = pending;
        
        const completed = applications.filter(a => a.status === 'ci_completed').length;
        const completedStat = document.querySelectorAll('.stat-card')[2]?.querySelector('h3');
        if (completedStat) completedStat.textContent = completed;
    }
}

// Fallback: Auto-refresh every 2 seconds (in case WebSocket fails)
// This ensures data is always up-to-date even if WebSocket connection drops
if (currentDashboard) {
    setInterval(refreshApplications, 2000); // Reduced from 5 seconds to 2 seconds
    console.log(`⚡ Real-time WebSocket updates enabled for ${currentDashboard} dashboard`);
    console.log(`🔄 Fallback polling every 2 seconds for maximum reliability`);
}
