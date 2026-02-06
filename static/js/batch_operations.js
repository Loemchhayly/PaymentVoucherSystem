/**
 * Batch Signature System - JavaScript Operations
 * Handles AJAX operations for batch creation, approval, and rejection
 */

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get CSRF token from Django
 */
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}

/**
 * Show toast notification
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 */
function showToast(title, message, type = 'info') {
    // Check if Bootstrap Toast is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Create toast element
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'primary'} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong>
                        <br>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        // Get or create toast container
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();

        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    } else {
        // Fallback to alert
        const icon = type === 'success' ? '✓' : type === 'warning' ? '⚠' : type === 'error' ? '✗' : 'ℹ';
        alert(`${icon} ${title}\n${message}`);
    }
}

/**
 * Format number as currency
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: 'USD')
 */
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

/**
 * Disable button with loading state
 * @param {HTMLElement} button - Button element
 * @param {string} loadingText - Text to show while loading
 */
function setButtonLoading(button, loadingText = 'Loading...') {
    button.disabled = true;
    button.dataset.originalHtml = button.innerHTML;
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
}

/**
 * Reset button from loading state
 * @param {HTMLElement} button - Button element
 */
function resetButton(button) {
    button.disabled = false;
    if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
    }
}

// ============================================================================
// BATCH SELECTION (Finance Manager)
// ============================================================================

/**
 * Toggle select all checkboxes
 * @param {HTMLInputElement} checkbox - Select all checkbox
 */
function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.doc-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
    updateSelection();
}

/**
 * Update selected documents count and total
 */
function updateSelection() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
    const count = checkboxes.length;
    let total = 0;

    checkboxes.forEach(cb => {
        const amount = parseFloat(cb.dataset.amount || 0);
        total += amount;
    });

    // Update UI
    const countElement = document.getElementById('selected-count');
    const totalElement = document.getElementById('selected-total');
    const createButton = document.getElementById('create-batch-btn');

    if (countElement) {
        countElement.textContent = count;
    }

    if (totalElement) {
        totalElement.textContent = formatCurrency(total);
    }

    if (createButton) {
        createButton.disabled = count === 0;
    }

    // Update select-all checkbox state
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        const allCheckboxes = document.querySelectorAll('.doc-checkbox');
        selectAllCheckbox.checked = allCheckboxes.length > 0 && count === allCheckboxes.length;
        selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
    }
}

/**
 * Create a new batch (Finance Manager)
 */
function createBatch() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');

    if (checkboxes.length === 0) {
        showToast('Error', 'Please select at least one document', 'error');
        return;
    }

    // Show notes modal
    const modal = document.getElementById('notesModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

/**
 * Submit batch creation
 */
function submitBatch() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
    const voucherIds = [];
    const formIds = [];

    checkboxes.forEach(cb => {
        if (cb.dataset.type === 'voucher') {
            voucherIds.push(cb.dataset.id);
        } else if (cb.dataset.type === 'form') {
            formIds.push(cb.dataset.id);
        }
    });

    const notes = document.getElementById('fm-notes')?.value || '';
    const submitButton = event.target;

    // Validate
    if (voucherIds.length === 0 && formIds.length === 0) {
        showToast('Error', 'Please select at least one document', 'error');
        return;
    }

    // Create FormData
    const formData = new FormData();
    voucherIds.forEach(id => formData.append('voucher_ids[]', id));
    formIds.forEach(id => formData.append('form_ids[]', id));
    formData.append('notes', notes);
    formData.append('csrfmiddlewaretoken', getCSRFToken());

    // Show loading state
    setButtonLoading(submitButton, 'Creating Batch...');

    // Submit AJAX request
    fetch('/vouchers/batch/create/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('notesModal'));
            if (modal) {
                modal.hide();
            }

            // Redirect to batch detail page - Django message will show there
            window.location.href = data.redirect_url;
        } else {
            showToast('Error', data.error || 'Failed to create batch', 'error');
            resetButton(submitButton);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Network error while creating batch', 'error');
        resetButton(submitButton);
    });
}

// ============================================================================
// MD BATCH APPROVAL
// ============================================================================

let currentBatchId = null;
let currentBatchNumber = null;

/**
 * Show sign confirmation modal
 * @param {number} batchId - Batch ID
 * @param {string} batchNumber - Batch number
 * @param {number} docCount - Number of documents
 */
function showSignModal(batchId, batchNumber, docCount) {
    currentBatchId = batchId;
    currentBatchNumber = batchNumber;

    // Update modal content
    const batchNumberElement = document.getElementById('sign-batch-number');
    const docCountElement = document.getElementById('sign-doc-count');
    const commentsField = document.getElementById('sign-comments');

    if (batchNumberElement) {
        batchNumberElement.textContent = batchNumber;
    }
    if (docCountElement) {
        docCountElement.textContent = docCount;
    }
    if (commentsField) {
        commentsField.value = '';
    }

    // Show modal
    const modal = document.getElementById('signModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

/**
 * Confirm batch signature (MD)
 */
function confirmSign() {
    const comments = document.getElementById('sign-comments')?.value || '';
    const signButton = document.getElementById('sign-confirm-btn');

    if (!currentBatchId) {
        showToast('Error', 'Invalid batch ID', 'error');
        return;
    }

    // Show loading state
    setButtonLoading(signButton, 'Signing...');

    // Create FormData
    const formData = new FormData();
    formData.append('comments', comments);
    formData.append('csrfmiddlewaretoken', getCSRFToken());

    // Submit AJAX request
    fetch(`/vouchers/batch/${currentBatchId}/sign/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Batch signed successfully!', 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('signModal'));
            if (modal) {
                modal.hide();
            }

            // Redirect
            setTimeout(() => {
                window.location.href = data.redirect_url || '/vouchers/md-dashboard/';
            }, 1500);
        } else {
            showToast('Error', data.error || 'Failed to sign batch', 'error');
            resetButton(signButton);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Network error while signing batch', 'error');
        resetButton(signButton);
    });
}

/**
 * Show reject confirmation modal
 * @param {number} batchId - Batch ID
 * @param {string} batchNumber - Batch number
 */
function showRejectModal(batchId, batchNumber) {
    currentBatchId = batchId;
    currentBatchNumber = batchNumber;

    // Update modal content
    const batchNumberElement = document.getElementById('reject-batch-number');
    const commentsField = document.getElementById('reject-comments');

    if (batchNumberElement) {
        batchNumberElement.textContent = batchNumber;
    }
    if (commentsField) {
        commentsField.value = '';
        commentsField.classList.remove('is-invalid');
    }

    // Show modal
    const modal = document.getElementById('rejectModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

/**
 * Confirm batch rejection (MD)
 */
function confirmReject() {
    const commentsField = document.getElementById('reject-comments');
    const comments = commentsField?.value.trim() || '';
    const rejectButton = document.getElementById('reject-confirm-btn');

    // Validate rejection reason
    if (!comments) {
        if (commentsField) {
            commentsField.classList.add('is-invalid');
        }
        showToast('Error', 'Please provide a rejection reason', 'error');
        return;
    }

    if (!currentBatchId) {
        showToast('Error', 'Invalid batch ID', 'error');
        return;
    }

    // Remove validation error
    if (commentsField) {
        commentsField.classList.remove('is-invalid');
    }

    // Show loading state
    setButtonLoading(rejectButton, 'Rejecting...');

    // Create FormData
    const formData = new FormData();
    formData.append('comments', comments);
    formData.append('csrfmiddlewaretoken', getCSRFToken());

    // Submit AJAX request
    fetch(`/vouchers/batch/${currentBatchId}/reject/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'Batch rejected', 'warning');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('rejectModal'));
            if (modal) {
                modal.hide();
            }

            // Redirect
            setTimeout(() => {
                window.location.href = data.redirect_url || '/vouchers/md-dashboard/';
            }, 1500);
        } else {
            showToast('Error', data.error || 'Failed to reject batch', 'error');
            resetButton(rejectButton);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Network error while rejecting batch', 'error');
        resetButton(rejectButton);
    });
}

// ============================================================================
// DATATABLES INITIALIZATION
// ============================================================================

/**
 * Initialize DataTable for batch document selection
 */
function initBatchSelectionDataTable() {
    const table = document.getElementById('batch-documents-table');

    if (!table || typeof $.fn.DataTable === 'undefined') {
        return;
    }

    $(table).DataTable({
        pageLength: 25,
        order: [[1, 'asc']], // Sort by document number
        columnDefs: [
            { orderable: false, targets: 0 }, // Checkbox column
            { orderable: false, targets: -1 }  // Actions column
        ],
        language: {
            search: "Search documents:",
            lengthMenu: "Show _MENU_ documents per page",
            info: "Showing _START_ to _END_ of _TOTAL_ documents",
            infoEmpty: "No documents available",
            infoFiltered: "(filtered from _TOTAL_ total documents)",
            zeroRecords: "No matching documents found"
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip'
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Note: DataTable initialization is handled in the template for custom logic
    // Update selection on page load
    if (document.querySelector('.doc-checkbox')) {
        updateSelection();
    }
});

// Export functions to global scope
window.toggleSelectAll = toggleSelectAll;
window.updateSelection = updateSelection;
window.createBatch = createBatch;
window.submitBatch = submitBatch;
window.showSignModal = showSignModal;
window.confirmSign = confirmSign;
window.showRejectModal = showRejectModal;
window.confirmReject = confirmReject;
window.showToast = showToast;
window.formatCurrency = formatCurrency;