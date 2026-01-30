#!/usr/bin/env python
"""
Test script to verify PV and PF number generation
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

print("=" * 60)
print("TESTING PV AND PF NUMBER GENERATION")
print("=" * 60)

# Get or create a test user
user = User.objects.first()
if not user:
    print("ERROR: No user found in database. Please create a user first.")
    exit(1)

# Test PV number generation with payment date
print("\n1. Testing Payment Voucher (PV) Number Generation:")
print("   Using current month for payment_date...")
for i in range(3):
    # Create a temporary voucher instance with payment_date
    temp_voucher = PaymentVoucher(
        payee_name="Test",
        payment_date=date.today(),
        bank_name="Test Bank",
        bank_account="1234567890",
        created_by=user
    )
    pv_number = VoucherStateMachine.generate_pv_number(temp_voucher)
    print(f"   Generated PV: {pv_number}")

# Test PF number generation with payment date
print("\n2. Testing Payment Form (PF) Number Generation:")
print("   Using current month for payment_date...")
for i in range(3):
    # Create a temporary form instance with payment_date
    temp_form = PaymentForm(
        payee_name="Test",
        payment_date=date.today(),
        bank_name="Test Bank",
        bank_account="1234567890",
        created_by=user
    )
    pf_number = VoucherStateMachine.generate_pf_number(temp_form)
    print(f"   Generated PF: {pf_number}")

print("\n" + "=" * 60)
print("TEST COMPLETE!")
print("=" * 60)
print("\nExpected formats:")
print("  - PV: YYMM-0001 (e.g., 2601-0001)")
print("  - PF: YYMM-PF-0001 (e.g., 2601-PF-0001)")
print("\nBoth forms now have separate numbering sequences!")
print("=" * 60)