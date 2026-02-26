"""
Web-based diagnostic views for checking batch integrity
Only accessible by superusers
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from vouchers.models import (
    BatchVoucherItem, BatchFormItem,
    PaymentVoucher, PaymentForm
)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def check_batch_integrity_web(request):
    """
    Web-based batch integrity checker
    Only accessible by superusers
    """
    # Get all existing voucher and form IDs
    existing_voucher_ids = set(PaymentVoucher.objects.values_list('id', flat=True))
    existing_form_ids = set(PaymentForm.objects.values_list('id', flat=True))

    # Check voucher batch items
    orphaned_vouchers = []
    for item in BatchVoucherItem.objects.select_related('batch'):
        if item.voucher_id not in existing_voucher_ids:
            orphaned_vouchers.append({
                'item_id': item.id,
                'voucher_id': item.voucher_id,
                'batch_id': item.batch.id,
                'batch_number': item.batch.batch_number,
                'batch_status': item.batch.status,
            })

    # Check form batch items
    orphaned_forms = []
    for item in BatchFormItem.objects.select_related('batch'):
        if item.payment_form_id not in existing_form_ids:
            orphaned_forms.append({
                'item_id': item.id,
                'form_id': item.payment_form_id,
                'batch_id': item.batch.id,
                'batch_number': item.batch.batch_number,
                'batch_status': item.batch.status,
            })

    context = {
        'total_vouchers': len(existing_voucher_ids),
        'total_forms': len(existing_form_ids),
        'orphaned_vouchers': orphaned_vouchers,
        'orphaned_forms': orphaned_forms,
        'total_orphans': len(orphaned_vouchers) + len(orphaned_forms),
    }

    return render(request, 'vouchers/diagnostic/batch_integrity.html', context)
