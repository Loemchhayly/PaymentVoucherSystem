#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple verification script to confirm MD users can view all documents
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from accounts.models import User
from vouchers.models import PaymentVoucher, PaymentForm
from vouchers.views import VoucherDetailView, FormDetailView

def verify_md_access():
    print("=" * 70)
    print("VERIFYING MD USER ACCESS")
    print("=" * 70)

    # Check MD users exist
    md_users = User.objects.filter(role_level=5)
    print(f"\nMD Users found: {md_users.count()}")

    if md_users.count() == 0:
        print("ERROR: No MD users found!")
        return False

    for md in md_users:
        print(f"  - {md.username}: is_staff={md.is_staff}, is_active={md.is_active}")

    # Get first MD user for testing
    md_user = md_users.first()
    print(f"\nTesting with MD user: {md_user.username}")

    # Test VoucherDetailView queryset
    print("\n" + "-" * 70)
    print("Testing Payment Vouchers")
    print("-" * 70)

    vouchers = PaymentVoucher.objects.all()
    print(f"Total vouchers in database: {vouchers.count()}")

    view = VoucherDetailView()
    view.request = type('Request', (), {'user': md_user})()
    queryset = view.get_queryset()

    accessible_vouchers = queryset.count()
    print(f"Vouchers accessible to MD: {accessible_vouchers}")

    if accessible_vouchers == vouchers.count():
        print("PASS: MD can access all vouchers")
    else:
        print(f"FAIL: MD can only access {accessible_vouchers}/{vouchers.count()} vouchers")
        return False

    # Test FormDetailView queryset
    print("\n" + "-" * 70)
    print("Testing Payment Forms")
    print("-" * 70)

    forms = PaymentForm.objects.all()
    print(f"Total forms in database: {forms.count()}")

    view = FormDetailView()
    view.request = type('Request', (), {'user': md_user})()
    queryset = view.get_queryset()

    accessible_forms = queryset.count()
    print(f"Forms accessible to MD: {accessible_forms}")

    if accessible_forms == forms.count():
        print("PASS: MD can access all forms")
    else:
        print(f"FAIL: MD can only access {accessible_forms}/{forms.count()} forms")
        return False

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print("\nRESULT: ALL CHECKS PASSED")
    print("MD users can view all documents without errors.")
    print("\nImportant notes:")
    print("- MD users CAN VIEW all documents (both PV and PF)")
    print("- MD users CANNOT APPROVE individual PENDING_L5 documents")
    print("- MD users must use Signature Batches for approvals")
    return True

if __name__ == '__main__':
    try:
        success = verify_md_access()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
