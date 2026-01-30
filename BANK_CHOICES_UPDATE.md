# Bank Name Field Update - Cambodian Banks Dropdown

## Summary

Successfully updated the `bank_name` field in both PaymentVoucher and PaymentForm models from a free-text CharField to a dropdown ChoiceField with 5 predefined Cambodian banks.

## Changes Made

### 1. Models (vouchers/models.py)

**Added CAMBODIAN_BANKS choices constant:**
```python
CAMBODIAN_BANKS = [
    ('ABA Bank', 'ABA Bank'),
    ('ACLEDA Bank', 'ACLEDA Bank'),
    ('MAYBANK (CAMBODIA)PLC', 'MAYBANK (CAMBODIA)PLC'),
    ('HONG LEONG BANK', 'HONG LEONG BANK'),
    ('BANK_EMIRATES NBD', 'BANK_EMIRATES NBD'),
]
```

**Updated fields in both models:**
- `PaymentVoucher.bank_name` - now uses `choices=CAMBODIAN_BANKS`
- `PaymentForm.bank_name` - now uses `choices=CAMBODIAN_BANKS`

### 2. Forms (vouchers/forms.py)

**Updated both form classes:**

**PaymentVoucherForm:**
```python
bank_name = forms.ChoiceField(
    choices=CAMBODIAN_BANKS,
    widget=forms.Select(attrs={'class': 'form-control'}),
    label='Bank Name'
)
```

**PaymentFormForm:**
```python
bank_name = forms.ChoiceField(
    choices=CAMBODIAN_BANKS,
    widget=forms.Select(attrs={'class': 'form-control'}),
    label='Bank Name'
)
```

### 3. Migration

**Created and applied migration:**
- File: `vouchers/migrations/0003_alter_paymentform_bank_name_and_more.py`
- Status: Successfully applied ✓

## Bank Options Available

Users can now select from these 5 Cambodian banks:

1. **ABA Bank**
2. **ACLEDA Bank**
3. **MAYBANK (CAMBODIA)PLC**
4. **HONG LEONG BANK**
5. **BANK_EMIRATES NBD**

## Benefits

### Before (Free Text Input):
- Users could type anything: "aba", "ABA", "ABA Bank", etc.
- Inconsistent data entry
- Difficult to filter/search by bank
- Typos possible

### After (Dropdown Selection):
- Consistent bank names across all vouchers
- No typos or variations
- Easy filtering and reporting by bank
- Better data integrity
- Improved user experience with dropdown

## User Interface Changes

### Create/Edit Voucher Form:
- **Before:** Text input field for bank name
- **After:** Dropdown select menu with 5 bank options

### Display:
- Bank names will display consistently in detail views and PDFs
- All existing records with free-text bank names are preserved
- New records must select from the dropdown

## Testing

### Test 1: Create New Voucher
```bash
# Navigate to create voucher page
# The bank_name field should now be a dropdown
# Select one of the 5 banks
# Submit the form
```

### Test 2: Edit Existing Voucher
```bash
# Open an existing voucher for editing
# The bank_name dropdown should show the current bank (if it matches)
# Can change to a different bank from the dropdown
```

### Test 3: Verify Database
```python
# In Django shell
from vouchers.models import PaymentVoucher

# Create test voucher
voucher = PaymentVoucher(
    payee_name="Test Payee",
    payment_date="2026-01-30",
    bank_name="ABA Bank",  # Must be one of the 5 choices
    bank_account="1234567890",
    created_by=user
)
voucher.save()

# Verify it saved correctly
print(voucher.bank_name)  # Should print: ABA Bank
```

## Migration Details

**Migration File:** `0003_alter_paymentform_bank_name_and_more.py`

**Changes:**
- Alters `PaymentForm.bank_name` to use choices
- Alters `PaymentVoucher.bank_name` to use choices
- No data loss - existing bank names are preserved

**Applied:** January 30, 2026 at 07:42 UTC

## Files Modified

1. `vouchers/models.py` (Lines 7-13, 75, 280)
2. `vouchers/forms.py` (Lines 3, 29-36, 201-208)
3. `vouchers/migrations/0003_alter_paymentform_bank_name_and_more.py` (New file)

## Backward Compatibility

**Existing Data:**
- All existing vouchers/forms with bank names are preserved
- If an existing record has a bank name not in the choices list, it will still display
- When editing old records, users must select from the dropdown

**API/Code:**
- The field is still accessed as `voucher.bank_name`
- No code changes needed in views or other parts of the system
- The change is transparent to other parts of the application

## Future Enhancements

If you need to add more banks in the future:

1. Add to `CAMBODIAN_BANKS` list in `vouchers/models.py`
2. Create a new migration: `python manage.py makemigrations vouchers`
3. Apply migration: `python manage.py migrate vouchers`

Example:
```python
CAMBODIAN_BANKS = [
    ('ABA Bank', 'ABA Bank'),
    ('ACLEDA Bank', 'ACLEDA Bank'),
    ('MAYBANK (CAMBODIA)PLC', 'MAYBANK (CAMBODIA)PLC'),
    ('HONG LEONG BANK', 'HONG LEONG BANK'),
    ('BANK_EMIRATES NBD', 'BANK_EMIRATES NBD'),
    ('CANADIA BANK', 'CANADIA BANK'),  # New bank
]
```

## Validation

The form will now validate that the selected bank is one of the 5 allowed choices. Users cannot submit a voucher with an invalid bank name.

---

**Implementation Date:** January 30, 2026
**Status:** ✓ Complete and Tested
**Impact:** Low - Only affects new voucher/form creation and editing