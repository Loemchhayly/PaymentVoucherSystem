"""
Context processors for making data available to all templates.
"""
from vouchers.models import PaymentVoucher, PaymentForm


def pending_approvals(request):
    """
    Add pending approvals count to template context.
    Available as {{ pending_count }} in all templates.

    Counts both Payment Vouchers (PV) and Payment Forms (PF) pending user's approval.
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

        # Total pending count (PV + PF)
        pending_count = pv_count + pf_count

        return {
            'pending_count': pending_count,
        }

    return {
        'pending_count': 0,
    }
