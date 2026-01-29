"""
Management command to reassign orphaned vouchers to appropriate approvers.

Usage:
    python manage.py reassign_vouchers
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from vouchers.models import PaymentVoucher
from workflow.state_machine import VoucherStateMachine


class Command(BaseCommand):
    help = 'Reassign vouchers that have no current_approver but are in pending status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Searching for orphaned vouchers...'))

        # Find vouchers that are in pending status but have no approver
        pending_statuses = ['PENDING_L2', 'PENDING_L3', 'PENDING_L4', 'PENDING_L5']
        orphaned_vouchers = PaymentVoucher.objects.filter(
            status__in=pending_statuses,
            current_approver__isnull=True
        )

        count = orphaned_vouchers.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned vouchers found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {count} orphaned voucher(s). Reassigning...'))

        reassigned = 0
        still_orphaned = 0

        for voucher in orphaned_vouchers:
            # Get appropriate approver for current status
            new_approver = VoucherStateMachine.get_next_approver(voucher.status)

            if new_approver:
                voucher.current_approver = new_approver
                voucher.save()
                reassigned += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [OK] PV#{voucher.pv_number} ({voucher.get_status_display()}) '
                        f'assigned to {new_approver.get_full_name()} ({new_approver.get_role_level_display()})'
                    )
                )
            else:
                still_orphaned += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  [SKIP] PV#{voucher.pv_number} ({voucher.get_status_display()}) '
                        f'- No user found with required role level'
                    )
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Reassigned: {reassigned}'))
        if still_orphaned > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Still orphaned: {still_orphaned} (create users with required role levels)'
                )
            )
        self.stdout.write(self.style.SUCCESS('Done!'))
