#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnostic script to check for orphaned batch items
Run this when MD reports 404 errors on batches
"""
import os
import sys
import django

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from vouchers.models import (
    BatchVoucherItem, BatchFormItem,
    PaymentVoucher, PaymentForm,
    SignatureBatch
)

def check_orphans():
    print("=" * 70)
    print("CHECKING FOR ORPHANED BATCH ITEMS")
    print("=" * 70)

    # Get all existing voucher and form IDs
    existing_voucher_ids = set(PaymentVoucher.objects.values_list('id', flat=True))
    existing_form_ids = set(PaymentForm.objects.values_list('id', flat=True))

    print(f"\nExisting in database:")
    print(f"  - Payment Vouchers: {len(existing_voucher_ids)} (IDs: {sorted(existing_voucher_ids)[:10]}...)")
    print(f"  - Payment Forms: {len(existing_form_ids)} (IDs: {sorted(existing_form_ids)[:10]}...)")

    # Check voucher batch items
    print("\n" + "-" * 70)
    print("CHECKING VOUCHER BATCH ITEMS")
    print("-" * 70)

    voucher_items = BatchVoucherItem.objects.all()
    print(f"Total voucher batch items: {voucher_items.count()}")

    orphaned_vouchers = []
    for item in voucher_items:
        if item.voucher_id not in existing_voucher_ids:
            batch = item.batch
            orphaned_vouchers.append({
                'item_id': item.id,
                'voucher_id': item.voucher_id,
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'batch_status': batch.status
            })

    if orphaned_vouchers:
        print(f"\n⚠ FOUND {len(orphaned_vouchers)} ORPHANED VOUCHER ITEM(S):")
        for orphan in orphaned_vouchers:
            print(f"\n  Batch Item #{orphan['item_id']}:")
            print(f"    - References voucher_id: {orphan['voucher_id']} (DELETED)")
            print(f"    - In batch: {orphan['batch_number']} (ID: {orphan['batch_id']})")
            print(f"    - Batch status: {orphan['batch_status']}")
    else:
        print("\n✓ No orphaned voucher items found")

    # Check form batch items
    print("\n" + "-" * 70)
    print("CHECKING FORM BATCH ITEMS")
    print("-" * 70)

    form_items = BatchFormItem.objects.all()
    print(f"Total form batch items: {form_items.count()}")

    orphaned_forms = []
    for item in form_items:
        if item.payment_form_id not in existing_form_ids:
            batch = item.batch
            orphaned_forms.append({
                'item_id': item.id,
                'form_id': item.payment_form_id,
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'batch_status': batch.status
            })

    if orphaned_forms:
        print(f"\n⚠ FOUND {len(orphaned_forms)} ORPHANED FORM ITEM(S):")
        for orphan in orphaned_forms:
            print(f"\n  Batch Item #{orphan['item_id']}:")
            print(f"    - References form_id: {orphan['form_id']} (DELETED)")
            print(f"    - In batch: {orphan['batch_number']} (ID: {orphan['batch_id']})")
            print(f"    - Batch status: {orphan['batch_status']}")
    else:
        print("\n✓ No orphaned form items found")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_orphans = len(orphaned_vouchers) + len(orphaned_forms)

    if total_orphans > 0:
        print(f"\n⚠ TOTAL ORPHANED ITEMS: {total_orphans}")
        print(f"  - Orphaned voucher items: {len(orphaned_vouchers)}")
        print(f"  - Orphaned form items: {len(orphaned_forms)}")
        print("\nTHESE WILL BE AUTOMATICALLY CLEANED UP when MD views the batch!")
        print("Or you can clean them up now by running:")
        print("  python manage.py cleanup_orphaned_batch_items")
    else:
        print("\n✓ NO ORPHANED ITEMS FOUND")
        print("All batch items reference valid documents.")

    # Check for batches affected
    if total_orphans > 0:
        affected_batches = set()
        for orphan in orphaned_vouchers:
            affected_batches.add(orphan['batch_number'])
        for orphan in orphaned_forms:
            affected_batches.add(orphan['batch_number'])

        print(f"\n\nAffected batches: {', '.join(sorted(affected_batches))}")

        for batch_num in sorted(affected_batches):
            batch = SignatureBatch.objects.get(batch_number=batch_num)
            print(f"\n  Batch {batch_num}:")
            print(f"    URL: /vouchers/batch/{batch.id}/detail/")
            print(f"    Status: {batch.status}")
            print(f"    Created by: {batch.created_by}")

if __name__ == '__main__':
    try:
        check_orphans()
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
