// Main JavaScript file for WhatsApp Internship System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // File upload handling
    var fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var fileName = e.target.files[0]?.name;
            var label = e.target.nextElementSibling;
            if (label && label.classList.contains('form-label')) {
                label.textContent = fileName || 'Choose file';
            }
        });
    });

    // Confirmation dialogs
    var confirmLinks = document.querySelectorAll('[data-confirm]');
    confirmLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            var message = link.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Auto-filtering functionality with debounce
    var searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(function(input) {
        var timeoutId;
        input.addEventListener('input', function(e) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(function() {
                // Trigger auto-filter
                var form = input.closest('form');
                if (form && input.getAttribute('data-auto-filter') === 'true') {
                    showLoadingIndicator();
                    form.submit();
                }
            }, 300); // Reduced delay for faster response
        });
    });

    // Auto-filtering for select dropdowns
    var autoFilterSelects = document.querySelectorAll('.auto-filter-select');
    autoFilterSelects.forEach(function(select) {
        select.addEventListener('change', function(e) {
            var form = select.closest('form');
            if (form) {
                showLoadingIndicator();
                form.submit();
            }
        });
    });

    // Copy to clipboard functionality
    var copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var targetId = button.getAttribute('data-target');
            var target = document.getElementById(targetId);
            
            if (target) {
                target.select();
                document.execCommand('copy');
                
                // Show feedback
                var originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                button.classList.add('btn-success');
                button.classList.remove('btn-primary');
                
                setTimeout(function() {
                    button.innerHTML = originalText;
                    button.classList.remove('btn-success');
                    button.classList.add('btn-primary');
                }, 2000);
            }
        });
    });

    // Real-time status updates
    var statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach(function(select) {
        select.addEventListener('change', function(e) {
            var applicationId = select.getAttribute('data-application-id');
            var newStatus = select.value;
            
            if (applicationId && newStatus) {
                updateApplicationStatus(applicationId, newStatus);
            }
        });
    });

    // Auto-refresh for dashboard
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        setInterval(function() {
            // Refresh statistics without full page reload
            refreshDashboardStats();
        }, 30000); // 30 seconds
    }
});

// Utility functions
function updateApplicationStatus(applicationId, status) {
    var formData = new FormData();
    formData.append('status', status);
    formData.append('send_notification', 'on');
    
    fetch(`/applications/${applicationId}/update_status`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Status updated successfully', 'success');
        } else {
            showNotification('Error updating status', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating status', 'danger');
    });
}

function showLoadingIndicator() {
    // Show loading spinner for auto-filter
    var filterForm = document.querySelector('.card form');
    if (filterForm) {
        var existingSpinner = filterForm.querySelector('.filter-loading');
        if (!existingSpinner) {
            var spinner = document.createElement('div');
            spinner.className = 'filter-loading position-absolute top-50 start-50 translate-middle';
            spinner.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Filtering...</span></div>';
            filterForm.style.position = 'relative';
            filterForm.appendChild(spinner);
        }
    }
}

function refreshDashboardStats() {
    fetch('/api/dashboard-stats')
    .then(response => response.json())
    .then(data => {
        // Update statistics cards
        updateStatsCard('total-internships', data.total_internships);
        updateStatsCard('total-applications', data.total_applications);
        updateStatsCard('pending-applications', data.pending_applications);
    })
    .catch(error => {
        console.error('Error refreshing stats:', error);
    });
}

function updateStatsCard(elementId, value) {
    var element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function showNotification(message, type = 'info') {
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    var container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
}

// Form submission with loading state
function submitFormWithLoading(formElement) {
    var submitBtn = formElement.querySelector('button[type="submit"]');
    if (submitBtn) {
        var originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        submitBtn.disabled = true;
        
        // Re-enable after form submission
        setTimeout(function() {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }, 3000);
    }
}

// Add loading state to forms
document.addEventListener('submit', function(e) {
    if (e.target.tagName === 'FORM') {
        submitFormWithLoading(e.target);
    }
});

// WhatsApp share functionality
function shareOnWhatsApp(message, phoneNumber = '') {
    var encodedMessage = encodeURIComponent(message);
    var url = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
    window.open(url, '_blank');
}

// Export functionality
function exportData(format, filters = {}) {
    var params = new URLSearchParams(filters);
    params.append('format', format);
    
    window.location.href = `/applications/export?${params.toString()}`;
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+N for new internship
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        window.location.href = '/internships/create';
    }
    
    // Ctrl+/ for search
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        var searchInput = document.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
});

// Print functionality
function printPage() {
    window.print();
}

// Table sorting
function sortTable(table, column, direction = 'asc') {
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort(function(a, b) {
        var aVal = a.children[column].textContent.trim();
        var bVal = b.children[column].textContent.trim();
        
        if (direction === 'asc') {
            return aVal.localeCompare(bVal);
        } else {
            return bVal.localeCompare(aVal);
        }
    });
    
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
}

// Mobile-friendly navigation
function toggleMobileMenu() {
    var navbar = document.querySelector('.navbar-collapse');
    if (navbar) {
        var bsCollapse = new bootstrap.Collapse(navbar);
        bsCollapse.toggle();
    }
}

// File size validation
function validateFileSize(input, maxSizeMB = 16) {
    var file = input.files[0];
    if (file) {
        var sizeMB = file.size / (1024 * 1024);
        if (sizeMB > maxSizeMB) {
            showNotification(`File size must be less than ${maxSizeMB}MB`, 'danger');
            input.value = '';
            return false;
        }
    }
    return true;
}

// Auto-save form data to localStorage
function autoSaveForm(formElement, storageKey) {
    var inputs = formElement.querySelectorAll('input, textarea, select');
    
    // Load saved data
    var savedData = localStorage.getItem(storageKey);
    if (savedData) {
        try {
            var data = JSON.parse(savedData);
            inputs.forEach(function(input) {
                if (data[input.name]) {
                    input.value = data[input.name];
                }
            });
        } catch (e) {
            console.error('Error loading saved form data:', e);
        }
    }
    
    // Save data on input
    inputs.forEach(function(input) {
        input.addEventListener('input', function() {
            var data = {};
            inputs.forEach(function(inp) {
                data[inp.name] = inp.value;
            });
            localStorage.setItem(storageKey, JSON.stringify(data));
        });
    });
    
    // Clear saved data on successful submit
    formElement.addEventListener('submit', function() {
        localStorage.removeItem(storageKey);
    });
}

// Initialize auto-save for create/edit forms
var createForm = document.querySelector('#create-internship-form');
if (createForm) {
    autoSaveForm(createForm, 'internship-form-draft');
}

var editForm = document.querySelector('#edit-internship-form');
if (editForm) {
    var internshipId = editForm.getAttribute('data-internship-id');
    autoSaveForm(editForm, `internship-edit-${internshipId}`);
}
