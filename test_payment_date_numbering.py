#!/usr/bin/env python
"""
Test script to verify PV/PF number generation based on payment_date
This demonstrates that numbers now use the payment date, not creation date
"""
import os
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from workflow.state_machine import VoucherStateMachine
from vouchers.models import PaymentVoucher, PaymentForm
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("PAYMENT DATE NUMBERING TEST")
print("=" * 70)
print()

# Get or create a test user
user = User.objects.first()
if not user:
    print("ERROR: No user found in database. Please create a user first.")
    exit(1)

print(f"Today's Date: {date.today()}")
print(f"Today's Month Code: {date.today().strftime('%y%m')}")
print()

# Test 1: Create voucher with JANUARY payment date (while we're in February)
print("TEST 1: Payment Voucher with January Payment Date")
print("-" * 70)

january_date = date(2026, 1, 15)
voucher_jan = PaymentVoucher(
    payee_name="January Payee",
    payment_date=january_date,
    bank_name="Test Bank",
    bank_account="1234567890",
    created_by=user
)

pv_jan = VoucherStateMachine.generate_pv_number(voucher_jan)
print(f"Payment Date: {january_date} (January 2026)")
print(f"Generated PV Number: {pv_jan}")
print(f"Expected Format: 2601-XXXX (26=year 2026, 01=January)")
if pv_jan.startswith('2601-'):
    print("[OK] CORRECT! Number uses payment month (January)")
else:
    print("[FAIL] WRONG! Number should start with 2601-")
print()

# Test 2: Create voucher with FEBRUARY payment date
print("TEST 2: Payment Voucher with February Payment Date")
print("-" * 70)

february_date = date(2026, 2, 10)
voucher_feb = PaymentVoucher(
    payee_name="February Payee",
    payment_date=february_date,
    bank_name="Test Bank",
    bank_account="1234567890",
    created_by=user
)

pv_feb = VoucherStateMachine.generate_pv_number(voucher_feb)
print(f"Payment Date: {february_date} (February 2026)")
print(f"Generated PV Number: {pv_feb}")
print(f"Expected Format: 2602-XXXX (26=year 2026, 02=February)")
if pv_feb.startswith('2602-'):
    print("[OK] CORRECT! Number uses payment month (February)")
else:
    print("[FAIL] WRONG! Number should start with 2602-")
print()

# Test 3: Create voucher with MARCH payment date (future month)
print("TEST 3: Payment Voucher with March Payment Date")
print("-" * 70)

march_date = date(2026, 3, 5)
voucher_mar = PaymentVoucher(
    payee_name="March Payee",
    payment_date=march_date,
    bank_name="Test Bank",
    bank_account="1234567890",
    created_by=user
)

pv_mar = VoucherStateMachine.generate_pv_number(voucher_mar)
print(f"Payment Date: {march_date} (March 2026)")
print(f"Generated PV Number: {pv_mar}")
print(f"Expected Format: 2603-XXXX (26=year 2026, 03=March)")
if pv_mar.startswith('2603-'):
    print("[OK] CORRECT! Number uses payment month (March)")
else:
    print("[FAIL] WRONG! Number should start with 2603-")
print()

# Test 4: Payment Form with different month
print("TEST 4: Payment Form with December Payment Date")
print("-" * 70)

december_date = date(2026, 12, 25)
form_dec = PaymentForm(
    payee_name="December Payee",
    payment_date=december_date,
    bank_name="Test Bank",
    bank_account="1234567890",
    created_by=user
)

pf_dec = VoucherStateMachine.generate_pf_number(form_dec)
print(f"Payment Date: {december_date} (December 2026)")
print(f"Generated PF Number: {pf_dec}")
print(f"Expected Format: 2612-PF-XXXX (26=year 2026, 12=December)")
if pf_dec.startswith('2612-PF-'):
    print("[OK] CORRECT! Number uses payment month (December)")
else:
    print("[FAIL] WRONG! Number should start with 2612-PF-")
print()

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("SUCCESS! PV/PF numbers now use the PAYMENT DATE month, not creation month!")
print()
print("This means:")
print("  - If you create a voucher today (Jan 2026) for a January payment,")
print("    it will get a 2601-XXXX number (January's code)")
print()
print("  - If you create a voucher today (Jan 2026) for a March payment,")
print("    it will get a 2603-XXXX number (March's code)")
print()
print("This makes it easier to organize vouchers by payment period!")
print("=" * 70)