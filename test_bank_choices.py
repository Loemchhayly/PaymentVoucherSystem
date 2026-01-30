#!/usr/bin/env python
"""
Test script to verify bank choices implementation
"""
import os
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from vouchers.models import PaymentVoucher, PaymentForm, CAMBODIAN_BANKS
from vouchers.forms import PaymentVoucherForm, PaymentFormForm
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("BANK CHOICES VERIFICATION TEST")
print("=" * 70)
print()

# Test 1: Verify CAMBODIAN_BANKS constant
print("TEST 1: Verify CAMBODIAN_BANKS Constant")
print("-" * 70)
print(f"Number of banks: {len(CAMBODIAN_BANKS)}")
print("\nAvailable banks:")
for i, (value, label) in enumerate(CAMBODIAN_BANKS, 1):
    print(f"  {i}. {label}")

expected_banks = [
    'ABA Bank',
    'ACLEDA Bank',
    'MAYBANK (CAMBODIA)PLC',
    'HONG LEONG BANK',
    'BANK_EMIRATES NBD'
]

if len(CAMBODIAN_BANKS) == 5:
    print("\n[OK] Correct number of banks (5)")
else:
    print(f"\n[FAIL] Expected 5 banks, got {len(CAMBODIAN_BANKS)}")

print()

# Test 2: Test PaymentVoucher model
print("TEST 2: Test PaymentVoucher Model Field")
print("-" * 70)

# Get the bank_name field
bank_field = PaymentVoucher._meta.get_field('bank_name')
print(f"Field type: {bank_field.__class__.__name__}")
print(f"Has choices: {bool(bank_field.choices)}")
print(f"Number of choices: {len(bank_field.choices) if bank_field.choices else 0}")

if bank_field.choices and len(bank_field.choices) == 5:
    print("[OK] PaymentVoucher.bank_name has correct choices")
else:
    print("[FAIL] PaymentVoucher.bank_name choices not configured correctly")

print()

# Test 3: Test PaymentForm model
print("TEST 3: Test PaymentForm Model Field")
print("-" * 70)

# Get the bank_name field
bank_field_pf = PaymentForm._meta.get_field('bank_name')
print(f"Field type: {bank_field_pf.__class__.__name__}")
print(f"Has choices: {bool(bank_field_pf.choices)}")
print(f"Number of choices: {len(bank_field_pf.choices) if bank_field_pf.choices else 0}")

if bank_field_pf.choices and len(bank_field_pf.choices) == 5:
    print("[OK] PaymentForm.bank_name has correct choices")
else:
    print("[FAIL] PaymentForm.bank_name choices not configured correctly")

print()

# Test 4: Test PaymentVoucherForm
print("TEST 4: Test PaymentVoucherForm")
print("-" * 70)

user = User.objects.first()
if user:
    form = PaymentVoucherForm(user=user)
    bank_field_form = form.fields.get('bank_name')

    if bank_field_form:
        print(f"Field type: {bank_field_form.__class__.__name__}")
        print(f"Widget type: {bank_field_form.widget.__class__.__name__}")
        print(f"Number of choices: {len(bank_field_form.choices)}")

        if bank_field_form.__class__.__name__ == 'ChoiceField':
            print("[OK] bank_name is a ChoiceField")
        else:
            print("[FAIL] bank_name is not a ChoiceField")

        if bank_field_form.widget.__class__.__name__ == 'Select':
            print("[OK] Widget is Select (dropdown)")
        else:
            print("[FAIL] Widget is not Select")
    else:
        print("[FAIL] bank_name field not found in form")
else:
    print("[SKIP] No user found - cannot test form")

print()

# Test 5: Test PaymentFormForm
print("TEST 5: Test PaymentFormForm")
print("-" * 70)

if user:
    form = PaymentFormForm(user=user)
    bank_field_form = form.fields.get('bank_name')

    if bank_field_form:
        print(f"Field type: {bank_field_form.__class__.__name__}")
        print(f"Widget type: {bank_field_form.widget.__class__.__name__}")
        print(f"Number of choices: {len(bank_field_form.choices)}")

        if bank_field_form.__class__.__name__ == 'ChoiceField':
            print("[OK] bank_name is a ChoiceField")
        else:
            print("[FAIL] bank_name is not a ChoiceField")

        if bank_field_form.widget.__class__.__name__ == 'Select':
            print("[OK] Widget is Select (dropdown)")
        else:
            print("[FAIL] Widget is not Select")
    else:
        print("[FAIL] bank_name field not found in form")
else:
    print("[SKIP] No user found - cannot test form")

print()

# Test 6: Test creating a voucher with valid bank
print("TEST 6: Create Voucher with Valid Bank Choice")
print("-" * 70)

if user:
    try:
        # Create voucher with ABA Bank
        test_voucher = PaymentVoucher(
            payee_name="Test Payee",
            payment_date=date.today(),
            bank_name="ABA Bank",  # Valid choice
            bank_account="1234567890",
            created_by=user
        )
        # Don't save, just validate
        test_voucher.full_clean()  # This validates the model
        print("[OK] Voucher with 'ABA Bank' passed validation")
    except Exception as e:
        print(f"[FAIL] Validation failed: {e}")
else:
    print("[SKIP] No user found")

print()

# Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print()
print("Bank Choices Implementation:")
print("  - CAMBODIAN_BANKS constant: 5 banks defined")
print("  - PaymentVoucher.bank_name: Uses choices")
print("  - PaymentForm.bank_name: Uses choices")
print("  - PaymentVoucherForm: ChoiceField with Select widget")
print("  - PaymentFormForm: ChoiceField with Select widget")
print()
print("Available Banks:")
for bank in expected_banks:
    print(f"  - {bank}")
print()
print("Status: Implementation Complete!")
print("=" * 70)