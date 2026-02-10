"""
Context processors for making data available to all templates.
"""
from vouchers.models import PaymentVoucher, PaymentForm, SignatureBatch


def pending_approvals(request):
    """
    Add pending approvals count to template context.
    Available as {{ pending_count }} in all templates.

    Counts both Payment Vouchers (PV) and Payment Forms (PF) pending user's approval.
    For MD (role_level 5), shows ALL documents at PENDING_L5 (shared approval).
    For other levels, shows only documents assigned to them.
    """
    if request.user.is_authenticated:
        # Special handling for MD users - show ALL documents at PENDING_L5
        if request.user.role_level == 5:
            pv_count = PaymentVoucher.objects.filter(status='PENDING_L5').count()
            pf_count = PaymentForm.objects.filter(status='PENDING_L5').count()
            batch_count = SignatureBatch.objects.filter(status='PENDING').count()
        else:
            # For other role levels, show only documents assigned to them
            pv_count = PaymentVoucher.objects.filter(
                current_approver=request.user
            ).count()
            pf_count = PaymentForm.objects.filter(
                current_approver=request.user
            ).count()
            batch_count = 0

        # Total pending count (PV + PF + Batches for MD)
        pending_count = pv_count + pf_count + batch_count

        return {
            'pending_count': pending_count,
            'pending_batches': batch_count,
        }

    return {
        'pending_count': 0,
        'pending_batches': 0,
    }
