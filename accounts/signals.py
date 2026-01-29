"""
Signals for accounts app.
Auto-reassign orphaned vouchers when new approvers are created or approved.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from vouchers.models import PaymentVoucher
from workflow.state_machine import VoucherStateMachine

User = get_user_model()


@receiver(post_save, sender=User)
def reassign_orphaned_vouchers(sender, instance, created, **kwargs):
    """
    When a user is created or their role/approval status changes,
    reassign any orphaned vouchers that need their role level.
    """
    # Only process if user is fully qualified as an approver
    if not (instance.is_active and instance.email_verified and
            instance.is_approved and instance.role_level):
        return

    # Determine which status this user can approve
    status_map = {
        2: 'PENDING_L2',
        3: 'PENDING_L3',
        4: 'PENDING_L4',
        5: 'PENDING_L5',
    }

    target_status = status_map.get(instance.role_level)
    if not target_status:
        return

    # Find orphaned vouchers at this level
    orphaned_vouchers = PaymentVoucher.objects.filter(
        status=target_status,
        current_approver__isnull=True
    )

    if orphaned_vouchers.exists():
        count = 0
        for voucher in orphaned_vouchers:
            # Reassign to this user (first available approver)
            new_approver = VoucherStateMachine.get_next_approver(voucher.status)
            if new_approver:
                voucher.current_approver = new_approver
                voucher.save()
                count += 1

        if count > 0:
            print(f"Auto-reassigned {count} orphaned voucher(s) to {instance.get_full_name()} ({instance.get_role_level_display()})")
