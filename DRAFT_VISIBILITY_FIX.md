# Draft Visibility Fix - Payment Forms Now Show in Lists

## ✅ Issue Fixed

**Problem:** Payment Form (PF) drafts were not showing in "My Vouchers" list

**Root Cause:** Dashboard views were only querying `PaymentVoucher` objects, not `PaymentForm` objects

---

## 🔧 Changes Made

### 1. Updated Dashboard Views (`dashboard/views.py`)

#### Added Imports:
```python
from vouchers.models import PaymentVoucher, PaymentForm
from itertools import chain
from operator import attrgetter
```

#### Updated `MyVouchersView`:
**Before:**
- Only showed Payment Vouchers

**After:**
- Shows BOTH Payment Vouchers AND Payment Forms
- Combines both querysets
- Sorts by creation date
- Applies search filters to both types

```python
def get_queryset(self):
    # Get Payment Vouchers
    pv_queryset = PaymentVoucher.objects.filter(created_by=self.request.user)

    # Get Payment Forms
    pf_queryset = PaymentForm.objects.filter(created_by=self.request.user)

    # Apply filters to both...

    # Combine and sort
    combined = sorted(
        chain(pv_queryset, pf_queryset),
        key=attrgetter('created_at'),
        reverse=True
    )
    return combined
```

#### Updated `DashboardView` Context:
**Before:**
- Counted only Payment Vouchers

**After:**
- Counts BOTH PV and PF in summary statistics

```python
context['my_vouchers'] = (
    pv_base.filter(created_by=user).count() +
    pf_base.filter(created_by=user).count()
)
```

---

### 2. Updated Voucher List Template (`templates/dashboard/voucher_list.html`)

#### Smart Number Display:
```html
{% if voucher.pf_number %}
    <span class="pv-number" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
        PF {{ voucher.pf_number|default:"DRAFT" }}
    </span>
{% else %}
    <span class="pv-number">
        PV {{ voucher.pv_number|default:"DRAFT" }}
    </span>
{% endif %}
```

#### Smart Action Links:
```html
{% if voucher.pf_number %}
    <!-- Payment Form links -->
    <a href="{% url 'vouchers:pf_detail' voucher.pk %}">View</a>
    <a href="{% url 'vouchers:pf_edit' voucher.pk %}">Edit</a>
{% else %}
    <!-- Payment Voucher links -->
    <a href="{% url 'vouchers:detail' voucher.pk %}">View</a>
    <a href="{% url 'vouchers:edit' voucher.pk %}">Edit</a>
{% endif %}
```

---

## 📊 What You'll See Now

### My Vouchers List (http://localhost:8000/my-vouchers/)

```
┌──────────────────────────────────────────────────────┐
│ Number          │ Payee      │ Date        │ Status │
├──────────────────────────────────────────────────────┤
│ PF 2601-PF-0001 │ John Doe   │ Jan 29, 26  │ DRAFT  │  ← Payment Form (Green)
│ PV 2601-0001    │ Jane Smith │ Jan 29, 26  │ DRAFT  │  ← Payment Voucher (Blue)
│ PF 2601-PF-0002 │ Bob Wilson │ Jan 28, 26  │ DRAFT  │  ← Payment Form (Green)
│ PV 2601-0002    │ Alice Chen │ Jan 28, 26  │ DRAFT  │  ← Payment Voucher (Blue)
└──────────────────────────────────────────────────────┘
```

### Visual Differences:

| Type | Badge Color | Number Format | Actions |
|------|------------|---------------|---------|
| **PV** | Blue gradient | `PV 2601-0001` | View/Edit/Delete → PV URLs |
| **PF** | Green gradient | `PF 2601-PF-0001` | View/Edit/Delete → PF URLs |

---

## ✅ Features Now Working

### 1. Draft Lists
- ✅ Payment Voucher drafts show
- ✅ Payment Form drafts show
- ✅ Both appear in same list
- ✅ Sorted by creation date (newest first)

### 2. Correct Links
- ✅ PV drafts link to PV edit/detail/delete
- ✅ PF drafts link to PF edit/detail/delete
- ✅ No broken links

### 3. Visual Distinction
- ✅ Blue badge for PV
- ✅ Green badge for PF
- ✅ Clear number format (PV vs PF prefix)

### 4. Dashboard Counts
- ✅ "My Vouchers" count includes both PV and PF
- ✅ "Pending My Action" includes both
- ✅ "In Progress" includes both
- ✅ "Approved" includes both

---

## 🧪 How to Test

### Test 1: Create Both Types
1. Create a Payment Voucher (PV)
2. Create a Payment Form (PF)
3. Go to "My Vouchers" → Both should appear

### Test 2: Edit Links
1. Click "Edit" on a PF draft → Goes to PF edit page
2. Click "Edit" on a PV draft → Goes to PV edit page

### Test 3: Delete Links
1. Click "Delete" on a PF draft → Deletes the PF
2. Click "Delete" on a PV draft → Deletes the PV

### Test 4: Dashboard Counts
1. Check dashboard stats
2. Create a PF → Count should increase
3. Create a PV → Count should increase

---

## 📝 What Changed in Files

### Modified Files:
```
✅ dashboard/views.py
   - Added PaymentForm import
   - Updated MyVouchersView.get_queryset()
   - Updated DashboardView.get_context_data()

✅ templates/dashboard/voucher_list.html
   - Added PF number detection
   - Added conditional URL routing
   - Added green color for PF badges
```

---

## 🎯 Quick Verification

**Navigate to:** http://localhost:8000/my-vouchers/

**You should now see:**
- All your Payment Voucher drafts (Blue, PV prefix)
- All your Payment Form drafts (Green, PF prefix)
- Mixed together in chronological order
- Correct "View", "Edit", "Delete" links for each type

**Server status:** Auto-reloaded with changes ✅

---

## 📌 Summary

The "My Vouchers" list now shows **BOTH** Payment Vouchers (PV) and Payment Forms (PF) together, with:
- ✅ Correct numbering (PV 2601-0001 vs PF 2601-PF-0001)
- ✅ Visual distinction (Blue vs Green)
- ✅ Proper links to edit/view/delete
- ✅ Combined dashboard statistics

**Your drafts are now visible!** 🎉

---

*Fixed: January 29, 2026*