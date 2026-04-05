# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django-based payment voucher approval system with a 5-level workflow for Garden City Water Park. The system manages two document types: Payment Vouchers (PV) and Payment Forms (PF), both flowing through the same approval chain with MD batch signature capability.

## Commands

### Development Server
```bash
# Activate virtual environment (Windows)
.\env\Scripts\activate

# Run development server
python manage.py runserver

# Access at http://localhost:8000
```

### Database
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Shell access
python manage.py shell
```

### Testing
```bash
# Run tests with pytest
pytest

# Run specific test file
pytest vouchers/tests/test_models.py

# Run with coverage
pytest --cov
```

### Static Files
```bash
# Collect static files for production
python manage.py collectstatic
```

### Database Configuration
- Development uses SQLite by default (controlled by `USE_SQLITE=True` in `.env`)
- Production can use PostgreSQL (set `USE_SQLITE=False` and configure DB settings in `.env`)

## Architecture

### Core Django Apps

1. **accounts** - User authentication and role management
   - Custom User model with 5 role levels (Account Payable → Account Supervisor → Finance Manager → General Manager → Managing Director)
   - User approval system: new accounts require admin approval (`is_approved` field)
   - Email verification required (`email_verified` field)
   - Digital signature images stored per user

2. **vouchers** - Document CRUD and business logic
   - Two document types: `PaymentVoucher` (PV) and `PaymentForm` (PF)
   - Auto-generated document numbers: `YYMM-NNNN` format (resets monthly based on payment_date)
   - Line items with multi-currency support (USD, KHR, THB)
   - 10% VAT calculation on line items
   - File attachments organized by document number
   - Company bank accounts for transfers
   - Department master data for line items

3. **workflow** - State machine and approval orchestration
   - `VoucherStateMachine` and `FormStateMachine` - handle state transitions
   - State flow: `DRAFT → PENDING_L2 → PENDING_L3 → PENDING_L4 → PENDING_L5 → APPROVED`
   - Side states: `ON_REVISION` (can resubmit), `REJECTED` (final)
   - `ApprovalHistory` and `FormApprovalHistory` - immutable audit trail with copied signatures
   - `NotificationService` - email notifications (sent in background threads)
   - `AutoAttachmentService` - auto-generates and attaches PDF when document approved
   - Batch signature system for MD: Finance Manager creates batches, MD signs multiple documents at once

4. **dashboard** - Dashboard views and filtering
   - Role-based dashboard showing pending approvals
   - Advanced filtering by status, date range, payee, etc.
   - Pending approval counts available via context processor

### Key Architectural Patterns

#### 1. State Machine Pattern
The workflow uses explicit state machines (`VoucherStateMachine`, `FormStateMachine`) for all document transitions:
- All transitions validated before execution
- Atomic database operations via `@transaction.atomic`
- Auto-assignment of next approver based on role level
- Prevents duplicate approvals from same user
- Immutable audit trail via `ApprovalHistory`/`FormApprovalHistory`

**Important**: MD (Level 5) users cannot approve individual PENDING_L5 documents. They must use signature batches (Finance Manager controls which documents to send).

#### 2. Document Numbering
- PV/PF numbers use format `YYMM-NNNN` based on `payment_date` field (not current date)
- Numbers assigned on first submission (DRAFT → PENDING_L2)
- Monthly counter reset handled in `VoucherStateMachine.generate_pv_number()` and `generate_pf_number()`
- Uses `.aggregate(Max('pv_number'))` to find next number

#### 3. Batch Signature System
Located in `vouchers/models.py`:
- `SignatureBatch` - groups multiple PENDING_L5 documents for MD signature
- `BatchVoucherItem` and `BatchFormItem` - join tables linking documents to batches
- Batch number format: `BATCH-YYYYMMDD-NNN`
- Uses PostgreSQL advisory locks or `select_for_update()` for race-free numbering
- Finance Manager creates batches, MD signs in bulk
- When batch signed, all included documents transition PENDING_L5 → APPROVED

#### 4. Multi-Currency Support
Documents and line items support USD, KHR, THB:
- Each line item has its own currency
- Grand total calculated per currency: `calculate_grand_total()` returns dict
- Display helper: `get_grand_total_display()` returns formatted string like "$100.00 + ៛40,000.00"

#### 5. Email Notifications
Handled by `workflow/services.py`:
- Sent in background threads for instant response (~0.1s instead of ~1s)
- Email on: submit, approve (to next approver), final approval, reject, return for revision
- Uses Django templates in `templates/workflow/emails/`
- Gmail SMTP configured via `.env` (requires App Password)

#### 6. PDF Generation
Auto-attached when document approved:
- `vouchers/pdf_generator.py` contains `VoucherPDFGenerator` and `FormPDFGenerator`
- Uses WeasyPrint for HTML → PDF conversion
- PDFs include all approval signatures from `ApprovalHistory`
- Auto-attachment triggered by `AutoAttachmentService.attach_pdf_to_approved_document()`

### Data Models Relationships

```
User (accounts.User)
  ├─ created vouchers (PaymentVoucher.created_by)
  ├─ pending vouchers (PaymentVoucher.current_approver)
  ├─ approval actions (ApprovalHistory.actor)
  └─ signature batches created (SignatureBatch.created_by)

PaymentVoucher / PaymentForm
  ├─ line_items (VoucherLineItem / FormLineItem)
  ├─ attachments (VoucherAttachment / FormAttachment)
  ├─ approval_history (ApprovalHistory / FormApprovalHistory)
  ├─ comments (VoucherComment / FormComment)
  └─ batch_items (BatchVoucherItem / BatchFormItem)

SignatureBatch
  ├─ voucher_items (BatchVoucherItem)
  └─ form_items (BatchFormItem)
```

### Role-Based Access Control

User role levels (1-5) determine workflow permissions:
- **Level 1** (Account Payable): Creates and submits documents
- **Level 2** (Account Supervisor): First reviewer
- **Level 3** (Finance Manager): Second reviewer, creates MD signature batches
- **Level 4** (General Manager): Third reviewer, decides if MD approval needed (always required now)
- **Level 5** (Managing Director): Final approver, signs via batches only

Assignment logic in `workflow/state_machine.py`:
- `get_next_approver(status)` - finds first active, verified, approved user with required role level
- Documents automatically routed to correct approver via `current_approver` field

### File Storage

```
media/
  ├── signatures/              # User signature images
  ├── profile_photos/          # User profile photos
  ├── approval_signatures/     # Copied signatures in approval history
  ├── voucher_attachments/     # Organized by PV number
  │   └── {PV_NUMBER}/         # e.g., 2601-0001/invoice.pdf
  └── form_attachments/        # Organized by PF number
      └── {PF_NUMBER}/         # e.g., 2601-0042/receipt.pdf
```

Attachment paths generated by:
- `voucher_attachment_path()` - for voucher files
- `form_attachment_path()` - for payment form files

### Custom Context Processor

`accounts/context_processors.py` provides `pending_approvals`:
- Adds `pending_vouchers_count` and `pending_forms_count` to all template contexts
- Shows pending approval counts in navbar for current user
- Filters by `current_approver=request.user` and PENDING_L* statuses

### Settings Configuration

Key settings in `PaymentVoucherSystem/settings.py`:
- `AUTH_USER_MODEL = 'accounts.User'` - custom user model
- `TIME_ZONE = 'Asia/Phnom_Penh'`
- `SESSION_COOKIE_AGE = 28800` (8 hours) - extended to 2 weeks if "Remember Me" checked
- `LOGIN_URL = 'accounts:login'`
- `LOGIN_REDIRECT_URL = 'dashboard:home'`
- Email settings configured via environment variables
- Database switches between SQLite (dev) and PostgreSQL (prod) via `USE_SQLITE` env var

### Common Patterns

#### Creating/Updating Documents
Always use the state machine for status changes:
```python
from workflow.state_machine import VoucherStateMachine

# Submit a voucher
VoucherStateMachine.transition(voucher, 'submit', user, comments='')

# Approve
VoucherStateMachine.transition(voucher, 'approve', user, comments='Looks good')

# For batch approvals
VoucherStateMachine.transition(voucher, 'approve', user, via_batch=True)
```

#### Document Number Generation
Numbers auto-assigned on first submission, but can be manually generated:
```python
voucher.pv_number = VoucherStateMachine.generate_pv_number(voucher)
```

#### Multi-Currency Totals
```python
# Get totals as dict: {'USD': Decimal('100.00'), 'KHR': Decimal('40000')}
totals = voucher.calculate_grand_total()

# Get formatted display: "$100.00 + ៛40,000.00"
display = voucher.get_grand_total_display()
```

#### Checking Permissions
```python
can_do, error = VoucherStateMachine.can_transition(voucher, 'approve', user)
if not can_do:
    messages.error(request, error)
```

### Environment Variables

Required in `.env`:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `USE_SQLITE` - Database selection (True for SQLite, False for PostgreSQL)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL settings
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` - Gmail SMTP (use App Password)
- `DEFAULT_FROM_EMAIL` - From email address
- `SITE_URL` - Base URL for email links

### Dependencies

Key packages:
- Django 6.0.1
- WeasyPrint 60.1+ (PDF generation)
- Pillow 10.2+ (image processing)
- django-crispy-forms + crispy-bootstrap5 (form rendering)
- django-environ (environment variables)
- pytest-django (testing)

### Development Notes

1. **User Account Activation**: New users must be approved by admin (`is_approved=True`), verify email (`email_verified=True`), and have `is_active=True` to fully participate in workflow.

2. **State Machine Validation**: Always validate transitions before attempting them. The state machine will raise `ValueError` if transition not allowed.

3. **Atomic Transactions**: All state transitions wrapped in `@transaction.atomic` to ensure data consistency.

4. **Email Timeouts**: Email sending has 10-second timeout to prevent hanging. Configure in settings via `EMAIL_TIMEOUT`.

5. **Document Numbers**: Use payment_date (not current date) for numbering to allow backdated documents with correct sequence.

6. **MD Batch Workflow**: MD users cannot approve PENDING_L5 individually - only via batch signatures. Finance Manager controls which documents go to MD.

7. **Duplicate Prevention**: State machine prevents same user from approving a document twice.

8. **Revision Workflow**: When document returned (ON_REVISION), all approval signatures cleared. Resubmission starts fresh approval chain.
