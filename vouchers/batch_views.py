"""
Batch Signature System Views
Allows Finance Manager to group approved vouchers and send to MD for bulk signature
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal

from .models import (
    PaymentVoucher, PaymentForm,
    SignatureBatch, BatchVoucherItem, BatchFormItem
)


# ============================================================================
# FINANCE MANAGER: BATCH SELECTION
# ============================================================================

@login_required
def batch_select_documents(request):
    """
    Finance Manager selects APPROVED vouchers/forms for batch signature
    Only accessible by Finance Manager (role_level 3)
    """
    # Check permission
    if request.user.role_level != 3:
        messages.error(request, 'Only Finance Managers can create signature batches')
        return redirect('dashboard:home')

    # Get IDs of documents already in PENDING batches to exclude them
    pending_voucher_ids = BatchVoucherItem.objects.filter(
        batch__status='PENDING'
    ).values_list('voucher_id', flat=True)

    pending_form_ids = BatchFormItem.objects.filter(
        batch__status='PENDING'
    ).values_list('payment_form_id', flat=True)

    # Get ALL APPROVED documents (not already in a pending batch)
    vouchers = PaymentVoucher.objects.filter(
        status='APPROVED'
    ).exclude(
        id__in=pending_voucher_ids
    ).select_related('created_by').prefetch_related('line_items').order_by('-created_at')

    forms = PaymentForm.objects.filter(
        status='APPROVED'
    ).exclude(
        id__in=pending_form_ids
    ).select_related('created_by').prefetch_related('line_items').order_by('-created_at')

    context = {
        'vouchers': vouchers,
        'forms': forms,
    }

    return render(request, 'vouchers/batch/select_documents.html', context)


@login_required
def batch_create(request):
    """
    Create a new signature batch from selected documents
    """
    # Check permission
    if request.user.role_level != 3:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        # Get selected voucher and form IDs
        voucher_ids = request.POST.getlist('voucher_ids[]')
        form_ids = request.POST.getlist('form_ids[]')
        fm_notes = request.POST.get('notes', '')

        # Validate at least one document selected
        if not voucher_ids and not form_ids:
            return JsonResponse({'error': 'Please select at least one document'}, status=400)

        # Create batch
        batch = SignatureBatch.objects.create(
            created_by=request.user,
            fm_notes=fm_notes
        )

        # Add vouchers to batch
        for voucher_id in voucher_ids:
            try:
                voucher = PaymentVoucher.objects.get(
                    id=voucher_id,
                    status='APPROVED'
                )
                BatchVoucherItem.objects.create(batch=batch, voucher=voucher)
            except PaymentVoucher.DoesNotExist:
                pass

        # Add forms to batch
        for form_id in form_ids:
            try:
                form = PaymentForm.objects.get(
                    id=form_id,
                    status='APPROVED'
                )
                BatchFormItem.objects.create(batch=batch, payment_form=form)
            except PaymentForm.DoesNotExist:
                pass

        # Add success message
        messages.success(request, f'Batch {batch.batch_number} created successfully with {batch.get_document_count()} document(s)!')

        return JsonResponse({
            'success': True,
            'batch_number': batch.batch_number,
            'document_count': batch.get_document_count(),
            'redirect_url': f'/vouchers/batch/{batch.id}/detail/'
        })

    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ============================================================================
# MD DASHBOARD
# ============================================================================

@login_required
def fm_batch_list(request):
    """
    Finance Manager view to track their created batches
    Only accessible by Finance Manager (role_level 3)
    """
    # Check permission
    if request.user.role_level != 3:
        messages.error(request, 'Only Finance Managers can access this page')
        return redirect('dashboard:home')

    # Get all batches created by this FM
    batches = SignatureBatch.objects.filter(
        created_by=request.user
    ).select_related('created_by', 'signed_by').prefetch_related(
        'voucher_items__voucher',
        'form_items__payment_form'
    ).order_by('-created_at')

    # Separate by status
    pending_batches = batches.filter(status='PENDING')
    signed_batches = batches.filter(status='SIGNED')
    rejected_batches = batches.filter(status='REJECTED')

    context = {
        'pending_batches': pending_batches,
        'signed_batches': signed_batches,
        'rejected_batches': rejected_batches,
        'pending_count': pending_batches.count(),
        'signed_count': signed_batches.count(),
        'rejected_count': rejected_batches.count(),
    }

    return render(request, 'vouchers/batch/fm_batch_list.html', context)


@login_required
def md_dashboard(request):
    """
    Managing Director dashboard to view and sign batches
    Only accessible by MD (role_level 5)
    """
    # Check permission
    if request.user.role_level != 5:
        messages.error(request, 'Only Managing Director can access this dashboard')
        return redirect('dashboard:home')

    # Get pending batches
    pending_batches = SignatureBatch.objects.filter(
        status='PENDING'
    ).select_related('created_by').prefetch_related(
        'voucher_items__voucher',
        'form_items__payment_form'
    ).order_by('-created_at')

    # Get signed batches (last 10)
    signed_batches = SignatureBatch.objects.filter(
        status='SIGNED'
    ).select_related('created_by', 'signed_by').order_by('-signed_at')[:10]

    context = {
        'pending_batches': pending_batches,
        'signed_batches': signed_batches,
        'pending_count': pending_batches.count(),
    }

    return render(request, 'vouchers/batch/md_dashboard.html', context)


@login_required
def batch_detail(request, batch_id):
    """
    View details of a signature batch
    """
    batch = get_object_or_404(
        SignatureBatch.objects.prefetch_related(
            'voucher_items__voucher__line_items',
            'form_items__payment_form__line_items'
        ),
        id=batch_id
    )

    # Check permission
    if request.user.role_level not in [3, 5]:  # FM or MD
        messages.error(request, 'You do not have permission to view this batch')
        return redirect('dashboard:home')

    context = {
        'batch': batch,
        'total_amount': batch.get_total_amount(),
        'total_amount_display': batch.get_total_amount_display(),
        'document_count': batch.get_document_count(),
    }

    return render(request, 'vouchers/batch/batch_detail.html', context)


@login_required
def batch_sign(request, batch_id):
    """
    MD signs all documents in a batch
    """
    # Check permission
    if request.user.role_level != 5:
        return JsonResponse({'error': 'Only MD can sign batches'}, status=403)

    batch = get_object_or_404(SignatureBatch, id=batch_id, status='PENDING')

    if request.method == 'POST':
        md_comments = request.POST.get('comments', '')

        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Update batch
        batch.status = 'SIGNED'
        batch.signed_by = request.user
        batch.signed_at = timezone.now()
        batch.signature_ip = ip_address
        batch.md_comments = md_comments
        batch.save()

        # Add comments to all vouchers in batch
        from workflow.models import VoucherComment, FormComment

        comment_text = f'✓ Signed via Batch {batch.batch_number}'
        if md_comments:
            comment_text += f'\n\nMD Comments: {md_comments}'

        for item in batch.voucher_items.all():
            VoucherComment.objects.create(
                voucher=item.voucher,
                user=request.user,
                comment=comment_text
            )

        # Add comments to all forms in batch
        for item in batch.form_items.all():
            FormComment.objects.create(
                payment_form=item.payment_form,
                user=request.user,
                comment=comment_text
            )

        # Add success message
        messages.success(request, f'Batch {batch.batch_number} signed successfully!')

        return JsonResponse({
            'success': True,
            'message': f'Successfully signed {batch.get_document_count()} documents in batch {batch.batch_number}',
            'redirect_url': '/vouchers/md-dashboard/'
        })

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def batch_reject(request, batch_id):
    """
    MD rejects a batch
    """
    # Check permission
    if request.user.role_level != 5:
        return JsonResponse({'error': 'Only MD can reject batches'}, status=403)

    batch = get_object_or_404(SignatureBatch, id=batch_id, status='PENDING')

    if request.method == 'POST':
        md_comments = request.POST.get('comments', '')

        if not md_comments:
            return JsonResponse({'error': 'Please provide rejection reason'}, status=400)

        # Update batch
        batch.status = 'REJECTED'
        batch.signed_by = request.user
        batch.signed_at = timezone.now()
        batch.md_comments = md_comments
        batch.save()

        # Add warning message
        messages.warning(request, f'Batch {batch.batch_number} rejected')

        return JsonResponse({
            'success': True,
            'message': f'Batch {batch.batch_number} rejected. Finance Manager will be notified.',
            'redirect_url': '/vouchers/md-dashboard/'
        })

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def batch_remove_document(request, batch_id):
    """
    MD removes a single document from a pending batch
    """
    # Check permission
    if request.user.role_level != 5:
        return JsonResponse({'error': 'Only MD can remove documents from batches'}, status=403)

    batch = get_object_or_404(SignatureBatch, id=batch_id, status='PENDING')

    if request.method == 'POST':
        doc_type = request.POST.get('doc_type')  # 'voucher' or 'form'
        doc_id = request.POST.get('doc_id')
        reason = request.POST.get('reason', '')

        if not reason:
            return JsonResponse({'error': 'Please provide a reason for removal'}, status=400)

        try:
            if doc_type == 'voucher':
                item = BatchVoucherItem.objects.get(batch=batch, voucher_id=doc_id)
                doc_number = item.voucher.pv_number
                item.delete()
            elif doc_type == 'form':
                item = BatchFormItem.objects.get(batch=batch, payment_form_id=doc_id)
                doc_number = item.payment_form.pf_number
                item.delete()
            else:
                return JsonResponse({'error': 'Invalid document type'}, status=400)

            # Check if batch is now empty
            if batch.get_document_count() == 0:
                batch.status = 'REJECTED'
                batch.signed_by = request.user
                batch.signed_at = timezone.now()
                batch.md_comments = f'All documents removed. Last removal reason: {reason}'
                batch.save()

                return JsonResponse({
                    'success': True,
                    'batch_empty': True,
                    'message': f'Document {doc_number} removed. Batch is now empty and marked as rejected.',
                    'redirect_url': '/vouchers/md-dashboard/'
                })

            # Recalculate total
            new_total = batch.get_total_amount_display()
            new_count = batch.get_document_count()

            return JsonResponse({
                'success': True,
                'batch_empty': False,
                'message': f'Document {doc_number} removed from batch',
                'new_total': new_total,
                'new_count': new_count
            })

        except (BatchVoucherItem.DoesNotExist, BatchFormItem.DoesNotExist):
            return JsonResponse({'error': 'Document not found in batch'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)