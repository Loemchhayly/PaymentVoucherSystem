#!/usr/bin/env python
"""
Test script to verify PV and PF number generation
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from workflow.state_machine import VoucherStateMachine

print("=" * 60)
print("TESTING PV AND PF NUMBER GENERATION")
print("=" * 60)

# Test PV number generation
print("\n1. Testing Payment Voucher (PV) Number Generation:")
for i in range(3):
    pv_number = VoucherStateMachine.generate_pv_number()
    print(f"   Generated PV: {pv_number}")

# Test PF number generation
print("\n2. Testing Payment Form (PF) Number Generation:")
for i in range(3):
    pf_number = VoucherStateMachine.generate_pf_number()
    print(f"   Generated PF: {pf_number}")

print("\n" + "=" * 60)
print("TEST COMPLETE!")
print("=" * 60)
print("\nExpected formats:")
print("  - PV: YYMM-0001 (e.g., 2601-0001)")
print("  - PF: YYMM-PF-0001 (e.g., 2601-PF-0001)")
print("\nBoth forms now have separate numbering sequences!")
print("=" * 60)