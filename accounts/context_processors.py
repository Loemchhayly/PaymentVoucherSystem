"""
Context processors for making data available to all templates.
"""
from vouchers.models import PaymentVoucher


def pending_approvals(request):
    """
    Add pending approvals count to template context.
    Available as {{ pending_count }} in all templates.
    """
    if request.user.is_authenticated:
        pending_count = PaymentVoucher.objects.filter(
            current_approver=request.user
        ).count()

        return {
            'pending_count': pending_count,
        }

    return {
        'pending_count': 0,
    }
