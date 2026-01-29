# Quick Start: PV Number Attachment Storage

## ✅ What Was Fixed

Your payment voucher system now properly organizes attachments using PV numbers!

### Before:
```
media/voucher_attachments/2026/01/random_file.pdf
media/voucher_attachments/2026/01/another_file.pdf
```
❌ Files scattered by date, hard to find

### After:
```
media/voucher_attachments/2601-0001/invoice.pdf
media/voucher_attachments/2601-0001/receipt.jpg
media/voucher_attachments/2601-0002/invoice.pdf
```
✅ All files for a voucher in one folder!

## 🚀 How It Works Now

1. **Create Voucher** → PV number generated immediately (e.g., 2601-0001)
2. **Upload Files** → Stored in `voucher_attachments/2601-0001/`
3. **Add More Files** → Same folder automatically
4. **Download Files** → All in one place

## 📋 For Existing Vouchers (Migration)

If you have existing vouchers with attachments in the old structure:

### Step 1: Backup First!
```bash
# Backup database
python manage.py dumpdata > backup_before_migration.json

# Backup files
# Windows: xcopy /E /I media media_backup
# Linux/Mac: cp -r media/ media_backup/
```

### Step 2: Test Migration (Dry Run)
```bash
python manage.py migrate_attachments --dry-run
```

This shows what will happen without actually moving files.

### Step 3: Run Migration
```bash
python manage.py migrate_attachments
```

Watch the output:
- ✅ `[OK]` - File migrated successfully
- ⚠️ `[SKIP]` - Already in correct location
- ❌ `[ERROR]` - Problem with this file

### Step 4: Verify
```bash
# Check the media folder structure
dir media\voucher_attachments  # Windows
ls media/voucher_attachments   # Linux/Mac
```

You should see folders like:
- `2601-0001/`
- `2601-0002/`
- `2601-0003/`

## 🎯 Using the New System

### Creating Voucher with Attachments

1. Go to **Create New Voucher**
2. Fill in voucher details
3. Scroll to **Attachments (Optional)** section
4. Click to upload or drag & drop files
5. See message: "Files will be organized using a PV number..."
6. Click **Save Voucher**
7. ✅ PV number generated + Files stored!

### Viewing Attachments

On voucher detail page, you'll see:
```
┌─────────────────────────────────────────┐
│ 📁 Storage: voucher_attachments/2601-0001 │
└─────────────────────────────────────────┘

📄 invoice.pdf          512 KB • Jan 28, 2026  [Download]
📄 receipt.jpg         128 KB • Jan 28, 2026  [Download]
```

## 🔍 Testing Your Installation

### Quick Test

1. Create a new voucher
2. Upload an attachment
3. Check the PV number (e.g., 2601-0001)
4. Navigate to: `media/voucher_attachments/2601-0001/`
5. Your file should be there!

### Automated Test

Run the test script:
```bash
python manage.py shell < test_pv_attachments.py
```

Expected output:
```
TEST 1: PV Number Generation on Creation
[OK] Voucher created with ID: 123
[OK] PV Number assigned: 2601-0001
✓ All tests completed!
```

## 🛠️ Troubleshooting

### PV Number Not Generated?

**Check:** `vouchers/views.py` line 50-51
```python
# Should have this code:
from workflow.state_machine import VoucherStateMachine
form.instance.pv_number = VoucherStateMachine.generate_pv_number()
```

### Files in Wrong Location?

**Check:** `vouchers/models.py` line 166
```python
# Should have this:
file = models.FileField(upload_to=voucher_attachment_path)
```

### Migration Errors?

**Common issues:**
1. File permissions - ensure media folder is writable
2. Missing files - old files were deleted
3. Disk space - migration needs temporary space

**Fix:**
```bash
# Check media folder permissions
# Windows: Right-click folder → Properties → Security
# Linux/Mac: ls -la media/

# Check disk space
# Windows: dir
# Linux/Mac: df -h
```

## 📁 Folder Structure Reference

```
C:\1work\learndjango\PaymentVoucherSystem\
│
├── media/
│   └── voucher_attachments/
│       ├── 2601-0001/          ← January 2026, voucher #1
│       │   ├── invoice.pdf
│       │   └── receipt.jpg
│       ├── 2601-0002/          ← January 2026, voucher #2
│       │   └── contract.pdf
│       ├── 2602-0001/          ← February 2026, voucher #1
│       │   └── quote.pdf
│       └── DRAFT-123/          ← Draft voucher (no PV yet)
│           └── temp.pdf
│
├── vouchers/
│   ├── models.py               ← ✅ Updated
│   ├── views.py                ← ✅ Updated
│   └── management/
│       └── commands/
│           └── migrate_attachments.py  ← ✅ New
│
├── workflow/
│   └── state_machine.py        ← ✅ Updated
│
└── templates/
    └── vouchers/
        ├── voucher_detail.html ← ✅ Updated
        └── voucher_form.html   ← ✅ Updated
```

## 💡 Pro Tips

1. **Backup Before Migration:** Always backup before running the migration command

2. **Test First:** Use `--dry-run` to preview what will happen

3. **Monitor Space:** Each voucher now has its own folder, plan storage accordingly

4. **Easy Archival:** Can zip entire PV folder for archival
   ```bash
   # Windows
   tar -czf 2601-0001.tar.gz media/voucher_attachments/2601-0001/

   # Linux/Mac
   tar -czf 2601-0001.tar.gz media/voucher_attachments/2601-0001/
   ```

5. **Backup by PV:** Easy to backup specific vouchers
   ```bash
   # Backup all January 2026 vouchers
   xcopy media\voucher_attachments\2601-* backup\  # Windows
   cp -r media/voucher_attachments/2601-* backup/  # Linux/Mac
   ```

## 🎓 Next Steps

1. ✅ Verify PV numbers are generated on new vouchers
2. ✅ Test uploading attachments
3. ✅ Check file locations in media folder
4. ✅ Run migration for existing attachments (if any)
5. ✅ Train users on new storage location display

## 📞 Need Help?

Check these files for details:
- **Full Documentation:** `PV_NUMBER_ATTACHMENT_FIXES.md`
- **Test Script:** `test_pv_attachments.py`
- **Migration Command:** `vouchers/management/commands/migrate_attachments.py`

## 🎉 You're All Set!

Your payment voucher system now has proper PV number-based attachment storage!

**Key Benefits:**
- ✅ Easy to find all files for a voucher
- ✅ Clean folder organization
- ✅ Better for backups and archival
- ✅ Compliance-friendly audit trail
- ✅ No file naming conflicts

Happy voucher processing! 🚀
