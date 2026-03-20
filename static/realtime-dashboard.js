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
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
});

// Listen for new application submissions
socket.on('new_application', function(data) {
    console.log('New application received via WebSocket:', data);
    // Immediately refresh the table
    refreshApplications();
});

// Listen for application updates
socket.on('application_updated', function(data) {
    console.log('Application updated via WebSocket:', data);
    // Immediately refresh the table
    refreshApplications();
});

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
        else if (app.status === 'rejected') badgeClass = 'danger';
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

// Fallback: Auto-refresh every 5 seconds (in case WebSocket fails)
if (currentDashboard) {
    setInterval(refreshApplications, 5000);
    console.log(`Real-time WebSocket updates enabled for ${currentDashboard} dashboard`);
}
