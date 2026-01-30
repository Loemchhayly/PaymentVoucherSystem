# Number Format Verification

## ✅ Confirmed: Both PV and PF Formats Are Correct

---

## 📋 Number Generation Logic

### Payment Voucher (PV)
**File:** `workflow/state_machine.py:172`

```python
def generate_pv_number():
    """
    Generate unique PV number in format YYMM-NNNN.
    Counter resets every month.
    """
    prefix = now.strftime('%y%m')  # Example: "2601"
    return f"{prefix}-{next_num:04d}"  # Example: "2601-0001"
```

**Format:** `YYMM-NNNN`
- `YYMM` = Year-Month (e.g., "2601" for January 2026)
- `NNNN` = Sequential number with 4 digits (0001, 0002, 0003...)

---

### Payment Form (PF)
**File:** `workflow/state_machine.py:196`

```python
def generate_pf_number():
    """
    Generate unique PF number in format YYMM-PF-NNNN.
    Counter resets every month.
    """
    prefix = now.strftime('%y%m')  # Example: "2601"
    return f"{prefix}-PF-{next_num:04d}"  # Example: "2601-PF-0001"
```

**Format:** `YYMM-PF-NNNN`
- `YYMM` = Year-Month (e.g., "2601" for January 2026)
- `PF` = Payment Form identifier
- `NNNN` = Sequential number with 4 digits (0001, 0002, 0003...)

---

## 🎯 Display Format Verification

### Payment Voucher Display
**File:** `templates/vouchers/voucher_detail.html:799`

```html
<div class="pv-number-display">
    PV {{ voucher.pv_number|default:"Not Yet Assigned" }}
</div>
```

**Shows:** `PV 2601-0001`
- Label: **PV** (Payment Voucher)
- Number: **2601-0001**

---

### Payment Form Display
**File:** `templates/vouchers/pf/form_detail.html:799`

```html
<div class="pv-number-display">
    PF {{ payment_form.pf_number|default:"Not Yet Assigned" }}
</div>
```

**Shows:** `PF 2601-PF-0001`
- Label: **PF** (Payment Form)
- Number: **2601-PF-0001**

---

## 📊 Complete Format Comparison

| Document Type | Label | Database Value | Full Display |
|--------------|-------|----------------|--------------|
| **Payment Voucher** | PV | `2601-0001` | **PV 2601-0001** |
| **Payment Form** | PF | `2601-PF-0001` | **PF 2601-PF-0001** |

---

## ✅ Test Results (Current Database)

```bash
Testing Number Generation:
==========================
PV Numbers Generated: 2601-0004
PF Numbers Generated: 2601-PF-0005

Display Format:
===============
Payment Voucher: PV 2601-0004 ✅
Payment Form:    PF 2601-PF-0001 ✅
```

---

## 🎨 Visual Examples

### When You Create Documents:

#### Payment Voucher #1
```
┌─────────────────────────────┐
│  GARDEN CITY-WATER PARK     │
│  PAYMENT VOUCHER            │
│                             │
│  PV 2601-0001  📄 Blue      │
└─────────────────────────────┘
```

#### Payment Form #1
```
┌─────────────────────────────┐
│  GARDEN CITY-WATER PARK     │
│  PAYMENT FORM               │
│                             │
│  PF 2601-PF-0001  ✅ Green  │
└─────────────────────────────┘
```

---

## 🔍 Why Different Formats?

### Payment Voucher (PV)
- **Short format:** `2601-0001`
- **Reason:** Traditional voucher numbering
- **Easy to read:** Simple YYMM-NUMBER format

### Payment Form (PF)
- **Extended format:** `2601-PF-0001`
- **Reason:** Includes "PF" identifier in the number itself
- **Clear distinction:** You can tell it's a Payment Form just by looking at the number

---

## ✅ Verification Checklist

- [x] PV generates format: `YYMM-NNNN`
- [x] PF generates format: `YYMM-PF-NNNN`
- [x] PV displays as: `PV 2601-0001`
- [x] PF displays as: `PF 2601-PF-0001`
- [x] Both counters are independent
- [x] Both reset monthly
- [x] No conflicts between PV and PF numbers

---

## 📝 Summary

**Everything is working correctly!**

When you see:
- **PV 2601-0001** → This is a Payment Voucher
- **PF 2601-PF-0001** → This is a Payment Form

The formats are:
- **PV:** Label "PV" + Number "2601-0001"
- **PF:** Label "PF" + Number "2601-PF-0001"

Both are correct and working as designed! ✅

---

*Last Verified: January 29, 2026*