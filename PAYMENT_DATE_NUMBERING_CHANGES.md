# Payment Date Numbering - Implementation Summary

## What Changed

The PV/PF numbering system has been updated to use the **payment date** instead of the **creation date** for generating voucher numbers.

## Previous Behavior

**Before:** Numbers were based on when you created the voucher
- Create voucher on Feb 15, 2026 with payment date Jan 20, 2026
- Result: `2602-0001` (February number, because created in February)

## New Behavior

**After:** Numbers are based on the payment date
- Create voucher on Feb 15, 2026 with payment date Jan 20, 2026
- Result: `2601-0001` (January number, because payment is in January)

## Benefits

1. **Better Organization**: All vouchers for a payment month have the same prefix
2. **Easier Searching**: Find all January payments by searching for `2601-*`
3. **Logical Grouping**: Vouchers are organized by payment period, not creation time
4. **Backdating Support**: Can create backdated vouchers with correct month codes

## Files Modified

### 1. workflow/state_machine.py
- Updated `generate_pv_number(voucher)` - now takes voucher parameter
- Updated `generate_pf_number(payment_form)` - now takes form parameter
- Both methods now use `payment_date.strftime('%y%m')` instead of `timezone.now()`

### 2. vouchers/views.py
- Line 52: Updated PV number generation in `VoucherCreateView`
- Line 531: Updated PF number generation in `FormCreateView`
- Both now pass the form instance to generate the number

### 3. Test Files Updated
- `test_pv_pf_numbers.py` - Updated to create test instances with payment_date
- `test_pv_attachments.py` - Updated to pass voucher instance to generator

## Examples

### Example 1: Multiple Payments in Different Months

**Scenario:** You're creating vouchers in January 2026

| Creation Date | Payment Date | PV Number    | Notes                    |
|---------------|--------------|--------------|--------------------------|
| Jan 30, 2026  | Jan 15, 2026 | `2601-0001`  | January payment         |
| Jan 30, 2026  | Jan 20, 2026 | `2601-0002`  | January payment         |
| Jan 30, 2026  | Feb 5, 2026  | `2602-0001`  | February payment        |
| Jan 30, 2026  | Feb 10, 2026 | `2602-0002`  | February payment        |
| Jan 30, 2026  | Mar 1, 2026  | `2603-0001`  | March payment           |

All created on the same day, but organized by payment month!

### Example 2: Backdating Vouchers

**Scenario:** It's February 15, 2026, but you need to create a voucher for a January payment

- Payment Date: January 20, 2026
- PV Number: `2601-0003` (January code, not February)

Perfect for catching up on documentation!

## Testing

Run the test script to verify the new behavior:

```bash
python test_payment_date_numbering.py
```

Expected output:
- January payment → `2601-XXXX` ✓
- February payment → `2602-XXXX` ✓
- March payment → `2603-XXXX` ✓
- December payment → `2612-PF-XXXX` ✓

## Technical Details

### Number Format

**Payment Voucher (PV):**
```
YYMM-NNNN
├─┬┘ └─┬─┘
│ │    └─── Sequential number (0001-9999) for this month
│ └──────── Month (01-12)
└────────── Year (last 2 digits)
```

**Payment Form (PF):**
```
YYMM-PF-NNNN
├─┬┘ │  └─┬─┘
│ │  │    └─── Sequential number (0001-9999) for this month
│ │  └──────── PF identifier
│ └─────────── Month (01-12)
└───────────── Year (last 2 digits)
```

### Counter Reset

- Counters reset every month
- Each month starts at 0001
- PV and PF have **separate** counters
- Example:
  - `2601-0001` (First PV in January)
  - `2601-PF-0001` (First PF in January)

## Migration Notes

**Existing Vouchers:**
- All existing vouchers keep their current numbers
- No migration needed
- Only **new** vouchers will use payment-date-based numbering

**Database Impact:**
- No schema changes required
- No data migration needed
- Existing records are not modified

## Code Example

### How It Works Now

```python
# Create a voucher with January payment date
voucher = PaymentVoucher(
    payee_name="Test Payee",
    payment_date=date(2026, 1, 15),  # January 15
    bank_name="Test Bank",
    bank_account="1234567890",
    created_by=user
)

# Generate PV number using payment_date
voucher.pv_number = VoucherStateMachine.generate_pv_number(voucher)
# Result: "2601-0001" (uses January from payment_date)

voucher.save()
```

### Generator Method

```python
@staticmethod
def generate_pv_number(voucher):
    """
    Generate unique PV number in format YYMM-NNNN.
    Counter resets every month based on payment date.
    """
    # Use payment date instead of current date for numbering
    prefix = voucher.payment_date.strftime('%y%m')

    # Get last number for this payment month
    last_pv = PaymentVoucher.objects.filter(
        pv_number__startswith=prefix
    ).aggregate(Max('pv_number'))['pv_number__max']

    if last_pv:
        last_num = int(last_pv.split('-')[1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:04d}"
```

## Summary

✅ **Changed:** Number generation now uses payment_date instead of current date
✅ **Benefit:** Better organization by payment period
✅ **Impact:** Only affects new vouchers/forms
✅ **Testing:** All tests pass successfully

---

**Date Implemented:** January 30, 2026
**Files Changed:** 5 files (2 source files, 3 test files)
**Breaking Changes:** None (backward compatible)