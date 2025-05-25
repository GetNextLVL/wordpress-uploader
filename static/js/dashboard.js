document.addEventListener('DOMContentLoaded', function() {
    // Update dashboard data every 30 seconds
    updateDashboard();
    setInterval(updateDashboard, 30000);
    
    // Process rows 26-27 button
    const processRows26_27Button = document.getElementById('process-rows-26-27');
    if (processRows26_27Button) {
        processRows26_27Button.addEventListener('click', function() {
            processSpecificRows26And27();
        });
    }
    
    // Custom row processing form
    const customRowForm = document.getElementById('custom-row-form');
    if (customRowForm) {
        customRowForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const startRow = document.getElementById('start-row').value;
            const endRow = document.getElementById('end-row').value;
            processCustomRows(startRow, endRow);
        });
    }
    
    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
});

function updateDashboard() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateStatusCards(data);
            updateActivityLog(data.recent_activity);
        })
        .catch(error => console.error('Error updating dashboard:', error));
}

function updateStatusCards(data) {
    document.querySelector('#pending-posts .h3').textContent = data.pending_posts;
    document.querySelector('#published-posts .h3').textContent = data.published_today;
    document.querySelector('#error-count .h3').textContent = data.error_count;
}

function updateActivityLog(activities) {
    const tbody = document.querySelector('#activity-log tbody');
    tbody.innerHTML = '';

    activities.forEach(activity => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(activity.timestamp)}</td>
            <td>${activity.action}</td>
            <td><span class="badge bg-${activity.status === 'success' ? 'success' : 'danger'}">${activity.status}</span></td>
            <td>${activity.details}</td>
        `;
        tbody.appendChild(row);
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Process rows 26 and 27 specifically
function processSpecificRows26And27() {
    const resultElement = document.getElementById('process-result');
    const button = document.getElementById('process-rows-26-27');
    
    // Disable button while processing
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    // Clear previous result
    resultElement.classList.remove('alert-success', 'alert-danger', 'd-none');
    resultElement.classList.add('alert-info');
    resultElement.innerHTML = 'Processing rows 26 and 27. This may take a moment...';
    
    // Make the API call using the new query parameter endpoint
    fetch('/api/process/rows?start=26&end=27', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        resultElement.classList.remove('alert-info');
        if (data.success) {
            resultElement.classList.add('alert-success');
            resultElement.innerHTML = 'Success! Rows 26 and 27 have been processed. Check the activity log for details.';
        } else {
            resultElement.classList.add('alert-danger');
            resultElement.innerHTML = `Error: ${data.error || 'Unknown error occurred'}`;
        }
        
        // Re-enable button
        button.disabled = false;
        button.innerHTML = '<i data-feather="play"></i> Process Rows 26-27';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
        
        // Update the dashboard after a short delay
        setTimeout(updateDashboard, 2000);
    })
    .catch(error => {
        console.error('Error processing rows:', error);
        resultElement.classList.remove('alert-info');
        resultElement.classList.add('alert-danger');
        resultElement.innerHTML = 'Error: Failed to connect to the server. Please try again.';
        
        // Re-enable button
        button.disabled = false;
        button.innerHTML = '<i data-feather="play"></i> Process Rows 26-27';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    });
}

// Process custom row range
function processCustomRows(startRow, endRow) {
    const resultElement = document.getElementById('process-result');
    const form = document.getElementById('custom-row-form');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Validate input
    if (!startRow || !endRow || parseInt(startRow) > parseInt(endRow)) {
        alert('Invalid row range. End row must be greater than or equal to start row.');
        return;
    }
    
    // Disable button while processing
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    // Clear previous result and show status
    resultElement.classList.remove('alert-success', 'alert-danger', 'd-none');
    resultElement.classList.add('alert-info');
    resultElement.innerHTML = `Processing rows ${startRow} to ${endRow}. This may take a moment...`;
    
    // Make the API call using the new endpoint with query parameters
    fetch(`/api/process/rows?start=${startRow}&end=${endRow}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        resultElement.classList.remove('alert-info');
        if (data.success) {
            resultElement.classList.add('alert-success');
            resultElement.innerHTML = `Success! Rows ${startRow} to ${endRow} have been processed. Check the activity log for details.`;
        } else {
            resultElement.classList.add('alert-danger');
            resultElement.innerHTML = `Error: ${data.error || 'Unknown error occurred'}`;
        }
        
        // Re-enable button
        submitButton.disabled = false;
        submitButton.innerHTML = '<i data-feather="play-circle"></i> Process';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
        
        // Update the dashboard after a short delay
        setTimeout(updateDashboard, 2000);
    })
    .catch(error => {
        console.error('Error processing rows:', error);
        resultElement.classList.remove('alert-info');
        resultElement.classList.add('alert-danger');
        resultElement.innerHTML = 'Error: Failed to connect to the server. Please try again.';
        
        // Re-enable button
        submitButton.disabled = false;
        submitButton.innerHTML = '<i data-feather="play-circle"></i> Process';
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    });
}
