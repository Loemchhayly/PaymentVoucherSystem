# Batch Signature System Documentation

## Overview
The Batch Signature System allows Finance Managers to group multiple approved payment vouchers and forms, then send them in batches to the Managing Director for bulk signature approval.

## System Components

### 1. Database Models (`vouchers/models.py`)
Created in migration `0007_signaturebatch_batchvoucheritem_batchformitem.py`:

- **SignatureBatch**: Main batch record
  - `batch_number`: Auto-generated (e.g., BATCH-2024-0001)
  - `status`: PENDING, SIGNED, or REJECTED
  - `created_by`: Finance Manager who created the batch
  - `signed_by`: MD who signed/rejected
  - `fm_notes`: Optional notes from Finance Manager
  - `md_comments`: MD's comments on signing/rejection

- **BatchVoucherItem**: Links Payment Vouchers to batches
- **BatchFormItem**: Links Payment Forms to batches

### 2. Backend Views (`vouchers/batch_views.py`)

#### Finance Manager Views:
- `batch_select_documents()` - Select approved documents for batching
- `batch_create()` - Create a new batch (AJAX)

#### MD Views:
- `md_dashboard()` - View pending and signed batches
- `batch_detail()` - View batch details
- `batch_sign()` - Sign all documents in a batch (AJAX)
- `batch_reject()` - Reject a batch (AJAX)

### 3. Frontend Templates

#### A. Finance Manager Templates

**`templates/vouchers/batch/select_documents.html`**
- Shows APPROVED vouchers/forms in a DataTable
- Real-time selection count and total display
- Purple gradient theme matching the system
- Checkboxes for document selection
- "Send to MD for Signature" button
- Optional notes modal

Features:
- DataTables integration for search/sort/pagination
- Responsive design
- Real-time total calculation
- Bootstrap 5 styling

#### B. MD Templates

**`templates/vouchers/batch/md_dashboard.html`**
- Shows pending batches as cards
- Badge showing count of pending batches
- Each card shows:
  - Batch number and status
  - Creator and creation date
  - Document count and total amount
  - Finance Manager notes (if any)
- Actions for each batch:
  - "View Details" button
  - "Sign All" button (green)
  - "Reject" button (red)
- Recently signed batches table
- Responsive card layout

**`templates/vouchers/batch/batch_detail.html`**
- Full batch information sidebar:
  - Status badge
  - Creator information
  - Document count
  - Total amount (highlighted)
  - FM notes
  - MD signature info (if signed)
  - MD comments (if any)
- Document list:
  - Separate tables for PV and PF
  - Links to view individual documents
  - Grand total calculation
- MD actions (if pending):
  - Sign All button
  - Reject button

### 4. JavaScript (`static/js/batch_operations.js`)

Comprehensive JavaScript library for batch operations:

#### Utility Functions:
- `getCSRFToken()` - Get Django CSRF token
- `showToast(title, message, type)` - Show Bootstrap toast notifications
- `formatCurrency(amount, currency)` - Format currency values
- `setButtonLoading(button, text)` - Show loading state
- `resetButton(button)` - Reset from loading state

#### Finance Manager Functions:
- `toggleSelectAll(checkbox)` - Select/deselect all documents
- `updateSelection()` - Update count and total in real-time
- `createBatch()` - Show notes modal
- `submitBatch()` - Submit batch creation via AJAX

#### MD Functions:
- `showSignModal(batchId, batchNumber, docCount)` - Show sign confirmation
- `confirmSign()` - Sign batch via AJAX
- `showRejectModal(batchId, batchNumber)` - Show reject modal
- `confirmReject()` - Reject batch via AJAX

#### DataTable Initialization:
- `initBatchSelectionDataTable()` - Initialize DataTables with custom config

## URL Routes

All routes are in the `vouchers` namespace:

```python
# Finance Manager
vouchers:batch_select         # GET  - Show document selection page
vouchers:batch_create         # POST - Create batch (AJAX)

# MD Dashboard
vouchers:md_dashboard         # GET  - MD dashboard with pending batches

# Batch Actions
vouchers:batch_detail         # GET  - View batch details
vouchers:batch_sign           # POST - Sign batch (AJAX)
vouchers:batch_reject         # POST - Reject batch (AJAX)
```

## User Roles & Permissions

### Finance Manager (role_level = 3)
Can access:
- `/vouchers/batch/select/` - Select documents
- All batch detail views (read-only)

### Managing Director (role_level = 5)
Can access:
- `/vouchers/md-dashboard/` - MD dashboard
- All batch detail views
- Sign/reject batch actions

## Workflow

1. **Finance Manager selects documents:**
   - Navigate to Batch Selection page
   - Use DataTable to search/filter approved documents
   - Select documents using checkboxes
   - See real-time count and total
   - Click "Send to MD for Signature"
   - Add optional notes for MD
   - Submit batch creation

2. **System creates batch:**
   - Generates unique batch number (BATCH-YYYY-NNNN)
   - Links selected documents to batch
   - Sets status to PENDING
   - Redirects to batch detail page

3. **MD reviews batch:**
   - See pending batch on MD Dashboard
   - Click "View Details" to see all documents
   - Review FM notes and document list
   - Options:
     - **Sign All**: Approve all documents in batch
     - **Reject**: Reject entire batch with reason

4. **MD signs batch:**
   - Click "Sign All" button
   - Add optional comments
   - Confirm signature
   - System updates:
     - Batch status to SIGNED
     - Records MD signature with timestamp and IP
     - Adds workflow notes to all documents
     - Creates audit trail

5. **MD rejects batch:**
   - Click "Reject" button
   - Provide rejection reason (required)
   - Confirm rejection
   - System updates:
     - Batch status to REJECTED
     - Records rejection with timestamp
     - Notifies Finance Manager

## Design Features

### Visual Design
- **Purple Gradient Theme**: Matches existing system (#667eea → #764ba2)
- **Bootstrap 5**: Modern, responsive components
- **Card-based Layout**: Clean, organized presentation
- **Status Badges**: Color-coded status indicators
- **Icons**: Bootstrap Icons for visual clarity

### User Experience
- **Real-time Updates**: Instant feedback on selections
- **Loading States**: Clear indication of processing
- **Toast Notifications**: Non-intrusive success/error messages
- **Confirmation Modals**: Prevent accidental actions
- **Responsive Design**: Works on all device sizes

### Data Presentation
- **DataTables**: Powerful search, sort, pagination
- **Grand Totals**: Clearly highlighted
- **Document Links**: Direct access to source documents
- **Audit Trail**: Complete signature history

## Technical Highlights

1. **AJAX Operations**: All batch actions use AJAX for smooth UX
2. **CSRF Protection**: Proper Django CSRF token handling
3. **Error Handling**: Comprehensive validation and error messages
4. **Accessibility**: Proper ARIA labels and semantic HTML
5. **Performance**: Efficient queries with select_related/prefetch_related
6. **Security**: Role-level permission checks on all views

## Installation & Setup

1. **Database Migration:**
   ```bash
   python manage.py migrate
   ```

2. **Collect Static Files:**
   ```bash
   python manage.py collectstatic
   ```

3. **Access URLs:**
   - Finance Manager: Navigate to Batch Selection from dashboard
   - MD: Navigate to MD Dashboard from main dashboard

## Files Created/Modified

### New Files:
- `vouchers/batch_views.py` - Backend views
- `vouchers/migrations/0007_signaturebatch_batchvoucheritem_batchformitem.py` - Database migration
- `templates/vouchers/batch/select_documents.html` - FM selection page
- `templates/vouchers/batch/md_dashboard.html` - MD dashboard
- `templates/vouchers/batch/batch_detail.html` - Batch detail page
- `static/js/batch_operations.js` - JavaScript operations

### Modified Files:
- `vouchers/urls.py` - Added batch routes
- `vouchers/models.py` - Added batch models

## Testing Checklist

### Finance Manager Tests:
- [ ] Can access batch selection page
- [ ] Can see all approved documents
- [ ] Can search/filter documents with DataTable
- [ ] Selection count updates in real-time
- [ ] Total amount calculates correctly
- [ ] Can create batch with selected documents
- [ ] Can add optional notes
- [ ] Redirects to batch detail after creation

### MD Tests:
- [ ] Can access MD dashboard
- [ ] Sees all pending batches
- [ ] Pending count badge is accurate
- [ ] Can view batch details
- [ ] Can sign batch successfully
- [ ] Can reject batch with reason
- [ ] Cannot reject without reason
- [ ] Signed batches appear in history

### Security Tests:
- [ ] Non-FM users cannot access batch selection
- [ ] Non-MD users cannot access MD dashboard
- [ ] Cannot sign batches that are already signed
- [ ] CSRF protection works on all AJAX calls

## Future Enhancements

Potential improvements:
1. Email notifications when batch is created/signed/rejected
2. Batch PDF export for printing
3. Batch filtering by date range
4. Batch search functionality
5. Batch approval delegation
6. Partial batch approval (approve individual documents)
7. Batch editing (add/remove documents before sending)
8. Integration with digital signature services

## Support

For issues or questions about the batch signature system, contact the development team or refer to the main system documentation.