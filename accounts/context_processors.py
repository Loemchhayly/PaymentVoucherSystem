"""
Context processors for making data available to all templates.
"""
from vouchers.models import PaymentVoucher, PaymentForm, SignatureBatch


def pending_approvals(request):
    """
    Add pending approvals count to template context.
    Available as {{ pending_count }} in all templates.

    Counts both Payment Vouchers (PV) and Payment Forms (PF) pending user's approval.
    For MD (role_level 5), also includes pending signature batches.
    """
    if request.user.is_authenticated:
        # Count Payment Vouchers pending user's approval
        pv_count = PaymentVoucher.objects.filter(
            current_approver=request.user
        ).count()

        # Count Payment Forms pending user's approval
        pf_count = PaymentForm.objects.filter(
            current_approver=request.user
        ).count()

        # Count pending signature batches for MD
        batch_count = 0
        if request.user.role_level == 5:  # Managing Director
            batch_count = SignatureBatch.objects.filter(status='PENDING').count()

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
