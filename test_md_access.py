#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify MD users can view all documents without errors
"""
import os
import sys
import django

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from vouchers.models import PaymentVoucher, PaymentForm
from vouchers.views import VoucherDetailView, FormDetailView

User = get_user_model()

def test_md_access():
    print("=" * 80)
    print("TESTING MD USER ACCESS TO DOCUMENTS")
    print("=" * 80)

    # Get MD user
    try:
        md_user = User.objects.get(username='MD')
        print(f"\n✓ MD User found: {md_user.username}")
        print(f"  - Full Name: {md_user.get_full_name()}")
        print(f"  - Role Level: {md_user.role_level}")
        print(f"  - Is Staff: {md_user.is_staff}")
        print(f"  - Is Active: {md_user.is_active}")
    except User.DoesNotExist:
        print("\n✗ MD user not found!")
        return False

    # Test Payment Vouchers
    print("\n" + "-" * 80)
    print("TESTING PAYMENT VOUCHERS ACCESS")
    print("-" * 80)

    vouchers = PaymentVoucher.objects.all()
    print(f"\nTotal Payment Vouchers: {vouchers.count()}")

    errors = []
    for voucher in vouchers:
        try:
            # Check if MD has access via queryset filter
            view = VoucherDetailView()
            view.request = type('Request', (), {'user': md_user})()
            queryset = view.get_queryset()

            accessible = queryset.filter(pk=voucher.pk).exists()

            if accessible:
                status = "✓ ACCESSIBLE"
            else:
                status = "✗ NOT ACCESSIBLE"
                errors.append(f"PV {voucher.pv_number} (ID: {voucher.pk}) not accessible")

            print(f"  {status} - PV {voucher.pv_number} (ID: {voucher.pk}, Status: {voucher.status})")

            # Check for potential data issues
            if not voucher.line_items.exists():
                print(f"    ⚠ WARNING: No line items")
            if not voucher.created_by:
                print(f"    ⚠ WARNING: No creator")
                errors.append(f"PV {voucher.pv_number} has no creator")

        except Exception as e:
            print(f"  ✗ ERROR - PV {voucher.pv_number} (ID: {voucher.pk}): {str(e)}")
            errors.append(f"PV {voucher.pv_number}: {str(e)}")

    # Test Payment Forms
    print("\n" + "-" * 80)
    print("TESTING PAYMENT FORMS ACCESS")
    print("-" * 80)

    forms = PaymentForm.objects.all()
    print(f"\nTotal Payment Forms: {forms.count()}")

    for form in forms:
        try:
            # Check if MD has access via queryset filter
            view = FormDetailView()
            view.request = type('Request', (), {'user': md_user})()
            queryset = view.get_queryset()

            accessible = queryset.filter(pk=form.pk).exists()

            if accessible:
                status = "✓ ACCESSIBLE"
            else:
                status = "✗ NOT ACCESSIBLE"
                errors.append(f"PF {form.pf_number} (ID: {form.pk}) not accessible")

            print(f"  {status} - PF {form.pf_number} (ID: {form.pk}, Status: {form.status})")

            # Check for potential data issues
            if not form.line_items.exists():
                print(f"    ⚠ WARNING: No line items")
            if not form.created_by:
                print(f"    ⚠ WARNING: No creator")
                errors.append(f"PF {form.pf_number} has no creator")

        except Exception as e:
            print(f"  ✗ ERROR - PF {form.pf_number} (ID: {form.pk}): {str(e)}")
            errors.append(f"PF {form.pf_number}: {str(e)}")

    # Test actual HTTP requests
    print("\n" + "-" * 80)
    print("TESTING ACTUAL HTTP REQUESTS")
    print("-" * 80)

    client = Client()
    client.force_login(md_user)

    # Test first 5 vouchers
    test_vouchers = list(vouchers[:5])
    print(f"\nTesting HTTP access to first {len(test_vouchers)} vouchers:")

    for voucher in test_vouchers:
        try:
            response = client.get(f'/vouchers/pv/{voucher.pk}/')
            if response.status_code == 200:
                print(f"  ✓ PV {voucher.pv_number} - HTTP 200 OK")
            elif response.status_code == 404:
                print(f"  ✗ PV {voucher.pv_number} - HTTP 404 NOT FOUND")
                errors.append(f"PV {voucher.pv_number} returns 404")
            else:
                print(f"  ⚠ PV {voucher.pv_number} - HTTP {response.status_code}")
                errors.append(f"PV {voucher.pv_number} returns {response.status_code}")
        except Exception as e:
            print(f"  ✗ PV {voucher.pv_number} - ERROR: {str(e)}")
            errors.append(f"PV {voucher.pv_number} HTTP error: {str(e)}")

    # Test first 3 forms
    test_forms = list(forms[:3])
    print(f"\nTesting HTTP access to first {len(test_forms)} forms:")

    for form in test_forms:
        try:
            response = client.get(f'/vouchers/pf/{form.pk}/')
            if response.status_code == 200:
                print(f"  ✓ PF {form.pf_number} - HTTP 200 OK")
            elif response.status_code == 404:
                print(f"  ✗ PF {form.pf_number} - HTTP 404 NOT FOUND")
                errors.append(f"PF {form.pf_number} returns 404")
            else:
                print(f"  ⚠ PF {form.pf_number} - HTTP {response.status_code}")
                errors.append(f"PF {form.pf_number} returns {response.status_code}")
        except Exception as e:
            print(f"  ✗ PF {form.pf_number} - ERROR: {str(e)}")
            errors.append(f"PF {form.pf_number} HTTP error: {str(e)}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if errors:
        print(f"\n✗ FOUND {len(errors)} ERROR(S):")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✓ ALL TESTS PASSED!")
        print("  MD user can access all documents without errors")
        return True

if __name__ == '__main__':
    success = test_md_access()
    exit(0 if success else 1)
