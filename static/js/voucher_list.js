// Voucher List JavaScript
// Wrap in IIFE and attach to window to ensure functions are available during SPA navigation
// Prevent multiple executions
if (window._voucherListScriptLoaded) {
    console.warn('Voucher list script already loaded, skipping re-initialization');
} else {
    window._voucherListScriptLoaded = true;

(function() {
    // currentFilters will be initialized from template via window.voucherListConfig
    window.currentFilters = window.voucherListConfig || {
        doc_type: 'all',
        search: '',
        search_field: 'all',
        month: '',
        page: 1
    };

    /* ─── Row navigation ─── */
    window.goToVoucher = function(e, url) {
    if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' ||
        e.target.tagName === 'BUTTON' || e.target.closest('a') ||
        e.target.closest('button') || e.target.closest('.row-actions')) return;
    window.location.href = url;
    };

    /* ─── Checkbox helpers ─── */
    window.toggleSelectAll = function(master) {
    document.querySelectorAll('.row-checkbox').forEach(cb => {
        cb.checked = master.checked;

        // Desktop: highlight table row
        const tableRow = cb.closest('tr');
        if (tableRow) {
            tableRow.classList.toggle('row-selected', master.checked);
        }

        // Mobile: highlight card
        const mobileCard = cb.closest('.mobile-voucher-card');
        if (mobileCard) {
            mobileCard.classList.toggle('selected', master.checked);
        }
    });
    updateBulkBar();
    };

    window.updateBulkBar = function() {
    const checked = document.querySelectorAll('.row-checkbox:checked');
    const all     = document.querySelectorAll('.row-checkbox');
    const bar     = document.getElementById('bulkActionBar');
    const countEl = document.getElementById('selectedCount');
    const master  = document.getElementById('selectAll');

    if (countEl) countEl.textContent = checked.length;
    if (bar)     bar.classList.toggle('visible', checked.length > 0);

    if (master) {
        master.indeterminate = checked.length > 0 && checked.length < all.length;
        master.checked       = checked.length === all.length && all.length > 0;
    }

    /* Highlight selected rows/cards (works for both desktop and mobile) */
    document.querySelectorAll('.row-checkbox').forEach(cb => {
        // Desktop: highlight table row
        const tableRow = cb.closest('tr');
        if (tableRow) {
            tableRow.classList.toggle('row-selected', cb.checked);
        }

        // Mobile: highlight card
        const mobileCard = cb.closest('.mobile-voucher-card');
        if (mobileCard) {
            mobileCard.classList.toggle('selected', cb.checked);
        }
    });
    };

    /* ─── Filters ─── */
    window.filterByDocType = function(type) {
    currentFilters.doc_type = type;
    currentFilters.page = 1;
    applyFilters(true); // Scroll when changing tabs
    };

    window.goToPage = function(pageNum) {
    currentFilters.page = pageNum;
    applyFilters(false); // Don't scroll on pagination
    };

    /* ─── Initialize Filter Buttons with proper event listeners for mobile ─── */
    function initializeFilterButtons() {
        document.querySelectorAll('.filter-tab').forEach(btn => {
            // Remove any existing listeners to avoid duplicates
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);

            // Add proper event listener that works on both desktop and mobile
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const type = this.getAttribute('data-type');
                if (type) {
                    window.filterByDocType(type);
                }
            }, { passive: false });

            // Also add touch event for better mobile responsiveness
            newBtn.addEventListener('touchend', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const type = this.getAttribute('data-type');
                if (type) {
                    window.filterByDocType(type);
                }
            }, { passive: false });
        });
    }

    // Initialize filter buttons on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFilterButtons);
    } else {
        initializeFilterButtons();
    }

    /* ═══════════════════════════════════════════
       SERVER-SIDE SEARCH (ALL PAGES)
    ═══════════════════════════════════════════ */
    let activeSearchField = window.voucherListConfig ? window.voucherListConfig.search_field : 'all';

    // Initialize active search field pill and clear button - prevent duplicate execution
    function initializeSearchUI() {
        if (window._searchUIInitialized) return;
        window._searchUIInitialized = true;

        document.querySelectorAll('.search-pill').forEach(p => {
            p.classList.toggle('active', p.dataset.field === activeSearchField);
        });

        // Show clear button if there's an initial search query
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('searchClearBtn');
        if (searchInput && clearBtn && searchInput.value.trim()) {
            clearBtn.style.display = 'flex';
        }

        // Set correct placeholder based on active field
        const placeholders = {
            all:    'Search number, payee, description, amount, date…',
            number: 'Search by doc number e.g. 2603-0004…',
            payee:  'Search by payee name…',
            description: 'Search by line item description…',
            amount: 'Search by amount e.g. 244.20…',
            date:   'Search by date e.g. Mar 12 or 2026…'
        };
        if (searchInput) {
            searchInput.placeholder = placeholders[activeSearchField] || placeholders.all;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSearchUI);
    } else {
        initializeSearchUI();
    }

    window.setSearchField = function(field) {
        activeSearchField = field;
        document.querySelectorAll('.search-pill').forEach(p => {
            p.classList.toggle('active', p.dataset.field === field);
        });

        /* Update placeholder */
        const placeholders = {
            all:    'Search number, payee, description, amount, date…',
            number: 'Search by doc number e.g. 2603-0004…',
            payee:  'Search by payee name…',
            description: 'Search by line item description…',
            amount: 'Search by amount e.g. 244.20…',
            date:   'Search by date e.g. Mar 12 or 2026…'
        };
        const input = document.getElementById('searchInput');
        input.placeholder = placeholders[field] || placeholders.all;
        input.focus();

        // Re-run search with new field
        const query = input.value.trim();
        if (query) {
            serverSearch(query);
        }
    };

    window.clearSearch = function() {
        const input = document.getElementById('searchInput');
        input.value = '';
        document.getElementById('searchClearBtn').style.display = 'none';
        currentFilters.search = '';
        currentFilters.page = 1;
        applyFilters(false); // Don't scroll when clearing search
        input.focus();
    };

    let searchTimeout;
    window.liveSearch = function(val) {
        const clearBtn = document.getElementById('searchClearBtn');
        if (clearBtn) clearBtn.style.display = val.trim() ? 'flex' : 'none';

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => serverSearch(val.trim()), 400); // 400ms debounce
    };

    function serverSearch(query) {
        currentFilters.search = query;
        currentFilters.search_field = activeSearchField;
        currentFilters.page = 1; // Reset to page 1 when searching
        applyFilters(false); // Don't scroll when searching
    }

    /* ═══════════════════════════════════════════
       MONTH/YEAR PICKER
    ═══════════════════════════════════════════ */
    let pickerYear = new Date().getFullYear();
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthNamesLong = ['January', 'February', 'March', 'April', 'May', 'June',
                            'July', 'August', 'September', 'October', 'November', 'December'];

    // Close picker when clicking outside
    document.addEventListener('click', function(e) {
        const popup = document.getElementById('monthPickerPopup');
        const btn = document.getElementById('monthPickerBtn');
        if (popup && btn && !popup.contains(e.target) && !btn.contains(e.target)) {
            popup.classList.remove('show');
        }
    });

    window.toggleMonthPicker = function(event) {
        console.log('toggleMonthPicker called');
        // Stop event propagation to prevent immediate close from document click handler
        if (event) {
            event.stopPropagation();
        }

        const popup = document.getElementById('monthPickerPopup');
        if (!popup) {
            console.error('Month picker popup not found');
            return;
        }

        popup.classList.toggle('show');
        console.log('Popup show class toggled, has show:', popup.classList.contains('show'));
        console.log('Popup computed styles:', window.getComputedStyle(popup).opacity, window.getComputedStyle(popup).display);

        if (popup.classList.contains('show')) {
            // Initialize year to current year or selected year
            if (currentFilters.month) {
                const [year] = currentFilters.month.split('-');
                pickerYear = parseInt(year);
            } else {
                pickerYear = new Date().getFullYear();
            }
            renderMonthPicker();
        }
    };

    window.changePickerYear = function(delta, event) {
        if (event) {
            event.stopPropagation();
        }
        pickerYear += delta;
        renderMonthPicker();
    };

    function renderMonthPicker() {
        console.log('renderMonthPicker called, year:', pickerYear);
        const yearEl = document.getElementById('pickerYear');
        const grid = document.getElementById('monthGrid');

        if (!yearEl || !grid) {
            console.error('Month picker elements not found', {yearEl, grid});
            return;
        }

        yearEl.textContent = pickerYear;
        grid.innerHTML = '';
        console.log('Building month grid...');

        for (let m = 0; m < 12; m++) {
            const monthStr = `${pickerYear}-${String(m + 1).padStart(2, '0')}`;
            const cell = document.createElement('div');
            cell.className = 'month-cell';
            cell.textContent = monthNames[m];
            cell.onclick = (e) => {
                e.stopPropagation();
                selectMonth(monthStr, m);
            };

            // Mark if this month has data (we'll enhance this with backend data later)
            // For now, highlight months that could potentially have data
            cell.classList.add('has-data');

            // Mark selected month
            if (currentFilters.month === monthStr) {
                cell.classList.add('selected');
            }

            grid.appendChild(cell);
        }
        console.log('Month grid built with', grid.children.length, 'cells');
    }

    function selectMonth(monthStr, monthIndex) {
        currentFilters.month = monthStr;
        currentFilters.page = 1;

        // Update button label
        const [year, month] = monthStr.split('-');
        document.getElementById('monthPickerLabel').textContent = `${monthNames[monthIndex]} ${year}`;
        document.getElementById('monthPickerBtn').classList.add('active');

        // Close popup
        document.getElementById('monthPickerPopup').classList.remove('show');

        // Apply filters
        applyFilters(false);
    }

    window.clearMonthFilter = function(event) {
        if (event) {
            event.stopPropagation();
        }

        currentFilters.month = '';
        currentFilters.page = 1;

        // Reset button label
        document.getElementById('monthPickerLabel').textContent = 'All time';
        document.getElementById('monthPickerBtn').classList.remove('active');

        // Close popup
        document.getElementById('monthPickerPopup').classList.remove('show');

        // Apply filters
        applyFilters(false);
    };

    // Initialize month picker button state on page load
    if (currentFilters.month) {
        const [year, month] = currentFilters.month.split('-');
        const monthIndex = parseInt(month) - 1;
        document.getElementById('monthPickerLabel').textContent = `${monthNames[monthIndex]} ${year}`;
        document.getElementById('monthPickerBtn').classList.add('active');
    }

function applyFilters(shouldScroll = false) {
    const tableBody = document.querySelector('.pv-table tbody');
    const mobileCards = document.getElementById('mobileVoucherCards');

    // Dim both desktop table and mobile cards
    if (tableBody) {
        tableBody.style.opacity = '0.4';
        tableBody.style.pointerEvents = 'none';
    }
    if (mobileCards) {
        mobileCards.style.opacity = '0.4';
        mobileCards.style.pointerEvents = 'none';
    }

    const params = new URLSearchParams();
    if (currentFilters.doc_type && currentFilters.doc_type !== 'all')
        params.set('doc_type', currentFilters.doc_type);
    if (currentFilters.search)
        params.set('search', currentFilters.search);
    if (currentFilters.search_field && currentFilters.search_field !== 'all')
        params.set('search_field', currentFilters.search_field);
    if (currentFilters.month)
        params.set('month', currentFilters.month);
    if (currentFilters.page > 1)
        params.set('page', currentFilters.page);

    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    window.history.pushState({filters: currentFilters}, '', newUrl);

    fetch(newUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => r.text())
        .then(html => {
            const parser  = new DOMParser();
            const doc     = parser.parseFromString(html, 'text/html');

            // Update desktop table
            const newTbody = doc.querySelector('.pv-table tbody');
            if (newTbody && tableBody) {
                tableBody.innerHTML = newTbody.innerHTML;
                tableBody.style.opacity = '1';
                tableBody.style.pointerEvents = 'auto';
            }

            // Update mobile cards
            const newMobileCards = doc.getElementById('mobileVoucherCards');
            if (newMobileCards && mobileCards) {
                mobileCards.innerHTML = newMobileCards.innerHTML;
                mobileCards.style.opacity = '1';
                mobileCards.style.pointerEvents = 'auto';
            }

            // Update pagination footer
            const newFooter     = doc.querySelector('.table-footer');
            const currentFooter = document.querySelector('.table-footer');
            if (newFooter) {
                if (currentFooter) currentFooter.innerHTML = newFooter.innerHTML;
                else document.querySelector('.table-container').insertAdjacentHTML('afterend', newFooter.outerHTML);
            } else if (currentFooter) {
                currentFooter.remove();
            }

            // Update active filter tab
            document.querySelectorAll('.filter-tab').forEach(tab => {
                tab.classList.toggle('active',
                    tab.getAttribute('data-type') === currentFilters.doc_type ||
                    (currentFilters.doc_type === 'all' && tab.getAttribute('data-type') === 'all')
                );
            });

            const master = document.getElementById('selectAll');
            if (master) master.checked = false;
            updateBulkBar();

            // Only scroll if explicitly requested (e.g., when changing tabs)
            if (shouldScroll) {
                document.querySelector('.vouchers-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        })
        .catch(() => {
            if (tableBody) {
                tableBody.style.opacity = '1';
                tableBody.style.pointerEvents = 'auto';
            }
            if (mobileCards) {
                mobileCards.style.opacity = '1';
                mobileCards.style.pointerEvents = 'auto';
            }
        });
}

// Prevent multiple popstate listeners
if (!window._popstateListenerAdded) {
    window._popstateListenerAdded = true;
    window.addEventListener('popstate', function(e) {
        if (e.state && e.state.filters) {
            currentFilters = e.state.filters;
            applyFilters(false); // Don't scroll on browser back/forward
        } else {
            location.reload();
        }
    });
}

    /* ═══════════════════════════════════════════
       BULK APPROVAL — Modal + Form Submission
    ═══════════════════════════════════════════ */
    window.showBulkModal = function(type) {
    const n = document.querySelectorAll('.row-checkbox:checked').length;
    console.log('showBulkModal called, type:', type, 'selected:', n);

    if (n === 0) {
        console.warn('No items selected');
        return;
    }

    if (type === 'approve') {
        document.getElementById('approve-count').textContent = n;
        document.getElementById('approve-comments').value = '';
    } else if (type === 'reject') {
        document.getElementById('reject-count').textContent = n;
        document.getElementById('reject-comments').value = '';
    } else if (type === 'submit') {
        const submitCountEl = document.getElementById('submit-count');
        const submitCommentsEl = document.getElementById('submit-comments');
        if (submitCountEl) submitCountEl.textContent = n;
        if (submitCommentsEl) submitCommentsEl.value = '';
        console.log('Submit modal elements found:', !!submitCountEl, !!submitCommentsEl);
    }

    const modal = document.getElementById(type + '-modal');
    if (!modal) {
        console.error('Modal not found:', type + '-modal');
        return;
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    console.log('Modal opened:', type);
    };

    window.hideBulkModal = function(type) {
    const modal = document.getElementById(type + '-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
    };

    window.confirmBulkAction = function(action) {
    const commentsEl = document.getElementById(action + '-comments');
    const comments   = commentsEl ? commentsEl.value.trim() : '';

    /* Reject requires a reason */
    if (action === 'reject' && !comments) {
        commentsEl.focus();
        commentsEl.style.borderColor = 'var(--danger)';
        commentsEl.style.boxShadow   = '0 0 0 3px rgba(239,68,68,0.15)';
        setTimeout(() => {
            commentsEl.style.borderColor = '';
            commentsEl.style.boxShadow   = '';
        }, 2000);
        return;
    }

    const selected = document.querySelectorAll('.row-checkbox:checked');
    if (!selected.length) return;

    const hiddenInputs  = document.getElementById('hidden-inputs');
    hiddenInputs.innerHTML = '';
    document.getElementById('action-input').value   = action;
    document.getElementById('comments-input').value = comments;

    selected.forEach(cb => {
        const inp  = document.createElement('input');
        inp.type   = 'hidden';
        inp.name   = cb.dataset.doctype === 'pf' ? 'pf_ids[]' : 'pv_ids[]';
        inp.value  = cb.value;
        hiddenInputs.appendChild(inp);
    });

    document.getElementById('bulk-action-form').submit();
    };

    /* Close on Escape - prevent duplicate listeners */
    if (!window._escapeListenerAdded) {
        window._escapeListenerAdded = true;
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                hideBulkModal('approve');
                hideBulkModal('reject');
                hideBulkModal('submit');
            }
        });
    }

    /* Close on overlay click - prevent duplicate listeners */
    if (!window._modalClickListenersAdded) {
        window._modalClickListenersAdded = true;
        ['approve-modal', 'reject-modal', 'submit-modal'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('click', function(e) {
                    if (e.target === this) hideBulkModal(id.replace('-modal', ''));
                });
            }
        });
    }

    /* ═══════════════════════════════════════════
       BULK SUBMIT DRAFTS — Modal + Form Submission
    ═══════════════════════════════════════════ */
    window.confirmBulkSubmit = function() {
        console.log('confirmBulkSubmit called');

        const commentsEl = document.getElementById('submit-comments');
        const comments = commentsEl ? commentsEl.value.trim() : '';

        const selected = document.querySelectorAll('.row-checkbox:checked');
        console.log('Selected checkboxes:', selected.length);

        if (!selected.length) {
            console.error('No checkboxes selected');
            return;
        }

        const hiddenInputs = document.getElementById('submit-hidden-inputs');
        if (!hiddenInputs) {
            console.error('submit-hidden-inputs element not found');
            return;
        }

        const form = document.getElementById('bulk-submit-form');
        if (!form) {
            console.error('bulk-submit-form not found');
            return;
        }

        hiddenInputs.innerHTML = '';
        document.getElementById('submit-comments-input').value = comments;

        selected.forEach(cb => {
            const inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = cb.dataset.doctype === 'pf' ? 'pf_ids[]' : 'pv_ids[]';
            inp.value = cb.value;
            hiddenInputs.appendChild(inp);
            console.log('Added input:', inp.name, '=', inp.value);
        });

        console.log('Form action:', form.action);
        console.log('Form method:', form.method);
        console.log('Submitting form...');
        form.submit();
    };

    // Execute immediately on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateBulkBar);
    } else {
        updateBulkBar();
    }
})();

} // End of script loaded check
