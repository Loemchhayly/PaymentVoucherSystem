# PV Number with Attachments Storage - Implementation Summary

## Overview
Fixed the payment voucher system to ensure PV numbers are properly generated and used for organizing file attachments.

## Changes Made

### 1. **models.py** - Attachment Storage Path
**File:** `vouchers/models.py`

**Added:**
- `voucher_attachment_path()` function to generate upload paths using PV numbers
- Format: `voucher_attachments/{PV_NUMBER}/filename.ext`
- Example: `voucher_attachments/2601-0001/invoice.pdf`
- Fallback for DRAFT vouchers: `voucher_attachments/DRAFT-{voucher_id}/filename.ext`

**Modified:**
```python
# OLD:
file = models.FileField(upload_to='voucher_attachments/%Y/%m/')

# NEW:
file = models.FileField(upload_to=voucher_attachment_path)
```

**Added Method:**
```python
def get_attachment_folder(self):
    """Get the folder path where attachments are stored"""
    if self.pv_number:
        return f"voucher_attachments/{self.pv_number}"
    return f"voucher_attachments/DRAFT-{self.id}"
```

### 2. **views.py** - Generate PV Number on Creation
**File:** `vouchers/views.py`

**Modified:** `VoucherCreateView.form_valid()`
- PV numbers are now generated **immediately** when voucher is created
- Previously generated only on submission

**Code Added:**
```python
# Generate PV number immediately upon creation
from workflow.state_machine import VoucherStateMachine
form.instance.pv_number = VoucherStateMachine.generate_pv_number()
```

**Result:**
- New vouchers get PV number like `2601-0001` right away
- Attachments uploaded during creation go directly to proper folder
- No need to move files later

### 3. **state_machine.py** - Handle Existing PV Numbers
**File:** `workflow/state_machine.py`

**Modified:** Submit action logic
- Now checks if PV number already exists before generating
- Prevents duplicate PV number generation

**Code Modified:**
```python
# OLD:
if voucher.status == 'DRAFT':
    voucher.pv_number = cls.generate_pv_number()

# NEW:
if voucher.status == 'DRAFT':
    if not voucher.pv_number:
        voucher.pv_number = cls.generate_pv_number()
```

### 4. **voucher_detail.html** - Display Storage Location
**File:** `templates/vouchers/voucher_detail.html`

**Added:**
- Storage location info box at top of attachments list
- File type icons (PDF, image, generic)
- Upload date display
- Storage path in upload form hint

**Visual Changes:**
```html
<!-- Storage location display -->
<div style="background: var(--primary-50); ...">
    <i class="bi bi-folder2-open"></i>
    <strong>Storage:</strong> {{ voucher.get_attachment_folder }}
</div>
```

### 5. **voucher_form.html** - Show Storage Info During Upload
**File:** `templates/vouchers/voucher_form.html`

**Added:**
- Storage location display for existing vouchers
- Info message for new vouchers about PV number generation
- Visual folder path indicator

## New Management Command

### migrate_attachments.py
**Location:** `vouchers/management/commands/migrate_attachments.py`

**Purpose:** Migrate existing attachments from old folder structure to new PV number-based structure

**Usage:**
```bash
# Dry run (preview changes)
python manage.py migrate_attachments --dry-run

# Actual migration
python manage.py migrate_attachments
```

**Features:**
- Safe migration with transaction support
- Dry-run mode to preview changes
- Detailed progress reporting
- Error handling and recovery
- Skips already migrated files

## Folder Structure

### OLD Structure (Date-based):
```
media/
└── voucher_attachments/
    ├── 2026/
    │   └── 01/
    │       ├── invoice_abc.pdf
    │       └── receipt_xyz.jpg
    └── 2026/
        └── 02/
            └── contract_def.pdf
```

### NEW Structure (PV Number-based):
```
media/
└── voucher_attachments/
    ├── 2601-0001/
    │   ├── invoice.pdf
    │   ├── receipt.jpg
    │   └── contract.pdf
    ├── 2601-0002/
    │   └── invoice.pdf
    └── DRAFT-123/
        └── temp_attachment.pdf
```

## Benefits

1. **Organization:** All files for a voucher in one folder
2. **Easy Identification:** Folder name = PV number
3. **Backup Friendly:** Can backup/restore by PV number
4. **Audit Trail:** Clear file organization for compliance
5. **No File Conflicts:** Each voucher has isolated folder

## Migration Steps

### For Existing Systems:

1. **Backup Database and Files:**
   ```bash
   # Backup database
   python manage.py dumpdata > backup.json

   # Backup media files
   cp -r media/ media_backup/
   ```

2. **Run Dry-Run Migration:**
   ```bash
   python manage.py migrate_attachments --dry-run
   ```

3. **Review Output:**
   - Check which files will be moved
   - Verify PV numbers are correct
   - Note any errors

4. **Run Actual Migration:**
   ```bash
   python manage.py migrate_attachments
   ```

5. **Verify Results:**
   - Check that files are in correct folders
   - Test downloading attachments
   - Verify database records updated

### For New Installations:

No migration needed! New attachments will automatically use PV number-based folders.

## Testing Checklist

- [ ] Create new voucher - verify PV number generated
- [ ] Upload attachment during creation - verify folder created
- [ ] Check file stored in: `voucher_attachments/{PV_NUMBER}/filename`
- [ ] Edit voucher and add more attachments - same folder
- [ ] Submit voucher - PV number remains same
- [ ] Download attachment - works correctly
- [ ] Delete voucher - attachments deleted too
- [ ] View voucher detail - storage location displayed
- [ ] Multiple files - all in same PV folder

## Rollback Plan

If issues occur:

1. **Restore Backup:**
   ```bash
   python manage.py loaddata backup.json
   cp -r media_backup/* media/
   ```

2. **Revert Code Changes:**
   ```bash
   git revert <commit-hash>
   ```

3. **Old Upload Path:**
   Change back to date-based in `models.py`:
   ```python
   file = models.FileField(upload_to='voucher_attachments/%Y/%m/')
   ```

## Security Considerations

1. **Path Sanitization:** `os.path.basename()` prevents directory traversal
2. **Access Control:** Download view checks permissions
3. **Isolated Folders:** Each PV has separate folder
4. **DRAFT Handling:** Uses voucher ID for pre-PV number files

## Performance Impact

- **Minimal:** File storage location change only
- **Database:** No additional queries
- **Migration:** One-time operation for existing files
- **Ongoing:** Same performance as before

## Future Enhancements

1. Auto-cleanup of empty DRAFT folders
2. Bulk file operations by PV number
3. Zip download all files for a voucher
4. File versioning within PV folder
5. Automatic file scanning/validation

## Support

For issues or questions:
1. Check Django error logs
2. Verify PV number generation working
3. Confirm file permissions on media folder
4. Test with single voucher first
5. Review migration command output

## Files Changed

1. `vouchers/models.py` - Upload path function and model method
2. `vouchers/views.py` - PV generation on creation
3. `workflow/state_machine.py` - PV number check logic
4. `templates/vouchers/voucher_detail.html` - Display storage info
5. `templates/vouchers/voucher_form.html` - Show storage location
6. `vouchers/management/commands/migrate_attachments.py` - New migration command

## Version

- **Date:** January 28, 2026
- **Django:** 6.0.1
- **Python:** 3.13.7
- **Status:** ✅ Implemented and Ready
