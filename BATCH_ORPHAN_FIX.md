# Fix: MD Receiving 404 Error for Deleted Vouchers in Batches

## Date: 2026-02-24

---

## 🐛 Problem Description

**Issue:** MD user received a 404 error when clicking on PV #24 from a signature batch, even though PV #24 doesn't exist in the database.

**Why it happens:**
1. A voucher (PV #24) was added to a Signature Batch
2. The voucher was later deleted from the database
3. The batch item (`BatchVoucherItem`) still referenced the deleted voucher
4. When MD clicked on the row in the batch detail page, it tried to open `/vouchers/pv/24/`
5. Result: **404 Error** - "No payment voucher found matching the query"

---

## 🔍 Root Cause Analysis

### Database Relationships
```python
class BatchVoucherItem(models.Model):
    batch = models.ForeignKey(SignatureBatch, on_delete=models.CASCADE)
    voucher = models.ForeignKey('PaymentVoucher', on_delete=models.CASCADE)
```

- The `on_delete=models.CASCADE` **should** automatically delete batch items when vouchers are deleted
- **However**, this doesn't protect against:
  - Race conditions (voucher deleted while batch is being viewed)
  - Direct database manipulation
  - Data integrity issues from previous bugs
  - Orphaned references if cascade fails

### How MD Clicks Generated 404

**In `batch_detail.html` (line 189):**
```html
<tr class="clickable-row" onclick="window.open('{% url 'vouchers:detail' item.voucher.id %}', '_blank')">
```

If `item.voucher` references a deleted voucher, clicking opens a non-existent URL.

---

## ✅ Solution Implemented

### 1. **Defensive View Logic** (`vouchers/batch_views.py`)

Added automatic detection and cleanup of orphaned batch items in `batch_detail()`:

```python
@login_required
def batch_detail(request, batch_id):
    """View details of a signature batch"""
    batch = get_object_or_404(SignatureBatch, id=batch_id)

    # DEFENSIVE CODING: Check for and remove orphaned batch items
    orphaned_voucher_items = []
    for item in batch.voucher_items.all():
        try:
            if not item.voucher or not PaymentVoucher.objects.filter(id=item.voucher_id).exists():
                orphaned_voucher_items.append(item)
        except (AttributeError, PaymentVoucher.DoesNotExist):
            orphaned_voucher_items.append(item)

    # Same for payment forms...

    # Remove orphaned items and notify user
    if orphaned_voucher_items or orphaned_form_items:
        # Delete orphaned items
        for item in orphaned_voucher_items:
            item.delete()

        messages.warning(
            request,
            f'Removed {orphan_count} deleted document(s) from this batch.'
        )
```

**Benefits:**
- ✅ Automatically detects orphaned batch items
- ✅ Removes them before rendering the page
- ✅ Notifies MD with a warning message
- ✅ Prevents 404 errors

---

### 2. **Template Safeguards** (`templates/vouchers/batch/batch_detail.html`)

Added conditional checks before rendering batch items:

**Before:**
```html
{% for item in batch.voucher_items.all %}
<tr onclick="window.open('{% url 'vouchers:detail' item.voucher.id %}', '_blank')">
    <td>{{ item.voucher.pv_number }}</td>
    ...
</tr>
{% endfor %}
```

**After:**
```html
{% for item in batch.voucher_items.all %}
{% if item.voucher %}
<tr onclick="window.open('{% url 'vouchers:detail' item.voucher.id %}', '_blank')">
    <td>{{ item.voucher.pv_number }}</td>
    ...
</tr>
{% else %}
<tr style="background-color: #fee2e2;">
    <td colspan="7" class="text-center">
        <small class="text-danger">
            <i class="bi bi-exclamation-triangle"></i>
            Document deleted - This batch item will be removed automatically
        </small>
    </td>
</tr>
{% endif %}
{% endfor %}
```

**Benefits:**
- ✅ Template won't crash if voucher is None
- ✅ Shows clear error message for deleted documents
- ✅ Prevents template rendering errors

---

### 3. **Cleanup Management Command**

Created `cleanup_orphaned_batch_items.py` to fix existing data:

```bash
python manage.py cleanup_orphaned_batch_items
```

**What it does:**
- Scans all batch items in the database
- Identifies items referencing deleted vouchers/forms
- Asks for confirmation
- Deletes orphaned batch items
- Provides detailed report

**Sample output:**
```
Checking for orphaned batch items...

Found 3 orphaned batch item(s):
  - 2 orphaned voucher items
  - 1 orphaned form items

Do you want to delete these orphaned items? (yes/no): yes

  - Deleted orphaned voucher item from batch #15
  - Deleted orphaned voucher item from batch #15
  - Deleted orphaned form item from batch #20

✓ Successfully deleted 3 orphaned batch item(s)!
Database cleanup complete.
```

---

## 🚀 How to Fix Existing Issues

### Step 1: Run Cleanup Command
```bash
python manage.py cleanup_orphaned_batch_items
```

This will find and remove all orphaned batch items from the database.

### Step 2: Verify Fix
1. Log in as MD user
2. Go to MD Dashboard → View existing signature batches
3. Open any batch that previously had errors
4. **Expected result:**
   - No 404 errors when clicking rows
   - Warning message if any orphaned items were found and removed
   - Batch displays correctly

---

## 📋 Prevention Measures

### Automatic Protection (Now Active)

1. **View-Level Cleanup**: Every time a batch is viewed, orphaned items are automatically removed
2. **Template Safeguards**: Template won't crash if voucher is None
3. **User Notifications**: MD sees clear warning when orphaned items are removed

### Best Practices Going Forward

1. **Don't Delete Documents in PENDING_L5 Status**
   - If a document is in a batch, don't delete it
   - Reject it instead, which properly updates status

2. **Use the Batch System Correctly**
   - Only add PENDING_L5 documents to batches
   - Once signed, documents become APPROVED
   - Once rejected, documents become REJECTED

3. **Regular Database Maintenance**
   - Run cleanup command monthly: `python manage.py cleanup_orphaned_batch_items`
   - Monitor for orphaned batch items

---

## 🎯 Testing Checklist

- [x] View batch with orphaned items → Items removed automatically
- [x] MD clicks on valid voucher in batch → Opens correctly
- [x] MD clicks on deleted voucher (if any remain) → No 404 error
- [x] Template handles None vouchers gracefully
- [x] Warning message displays when orphaned items removed
- [x] Cleanup command works correctly
- [x] No crashes or template errors

---

## 📝 Files Modified

1. **vouchers/batch_views.py**
   - Added orphaned item detection and cleanup in `batch_detail()`

2. **templates/vouchers/batch/batch_detail.html**
   - Added conditional checks: `{% if item.voucher %}`
   - Added error row for deleted documents

3. **vouchers/management/commands/cleanup_orphaned_batch_items.py** (NEW)
   - Management command to clean up existing orphaned batch items

---

## 🎉 Result

**Before:**
- ❌ MD clicks on deleted voucher → 404 Error
- ❌ Confusing error message
- ❌ No way to fix orphaned items

**After:**
- ✅ Orphaned items automatically detected and removed
- ✅ Clear warning message to MD
- ✅ No 404 errors
- ✅ Clean, stable batch system
- ✅ Management command to fix existing data

---

## 🔄 Future Improvements

1. **Prevent Deletion of Documents in Batches**
   - Add check in voucher/form delete views
   - Show error: "Cannot delete - document is in a pending signature batch"

2. **Batch Integrity Checks**
   - Daily cron job to check batch integrity
   - Email alerts for orphaned items

3. **Audit Trail**
   - Log when documents are deleted
   - Track which batches were affected

---

**Status: ✅ FIXED AND DEPLOYED**

MD users can now view signature batches without encountering 404 errors for deleted vouchers!
