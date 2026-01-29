from django.core.management.base import BaseCommand
from django.db.models import Count
from workflow.models import ApprovalHistory


class Command(BaseCommand):
    help = 'Find and remove duplicate approval records from the same user on the same voucher'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--voucher-id',
            type=int,
            help='Check specific voucher ID only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        voucher_id = options.get('voucher_id')

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Finding Duplicate Approval Records'))
        self.stdout.write(self.style.WARNING('=' * 70))

        # Build query
        approvals_query = ApprovalHistory.objects.filter(action='APPROVE')

        if voucher_id:
            approvals_query = approvals_query.filter(voucher_id=voucher_id)
            self.stdout.write(f'\nChecking voucher ID: {voucher_id}')
        else:
            self.stdout.write('\nChecking all vouchers')

        # Find vouchers with duplicate approvals from same user
        from django.db.models import Q
        from vouchers.models import PaymentVoucher

        vouchers_to_check = approvals_query.values('voucher_id').distinct()

        total_removed = 0
        vouchers_fixed = 0

        for voucher_data in vouchers_to_check:
            vid = voucher_data['voucher_id']

            # Get approvals for this voucher grouped by actor
            from collections import defaultdict
            approvals_by_actor = defaultdict(list)

            voucher_approvals = ApprovalHistory.objects.filter(
                voucher_id=vid,
                action='APPROVE'
            ).order_by('timestamp')

            for approval in voucher_approvals:
                approvals_by_actor[approval.actor_id].append(approval)

            # Find actors with multiple approvals
            has_duplicates = False
            for actor_id, approvals in approvals_by_actor.items():
                if len(approvals) > 1:
                    has_duplicates = True
                    actor = approvals[0].actor
                    vouchers_fixed += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f'\n✗ Voucher ID {vid}: {actor.get_full_name() or actor.username} '
                            f'has {len(approvals)} duplicate approvals'
                        )
                    )

                    # Keep the first one, remove the rest
                    to_keep = approvals[0]
                    to_remove = approvals[1:]

                    self.stdout.write(f'  ✓ Keeping: ID {to_keep.id} - {to_keep.timestamp}')

                    for duplicate in to_remove:
                        self.stdout.write(
                            self.style.WARNING(f'  ✗ Removing: ID {duplicate.id} - {duplicate.timestamp}')
                        )

                        if not dry_run:
                            duplicate.delete()
                            total_removed += 1
                        else:
                            total_removed += 1

        self.stdout.write(self.style.WARNING('\n' + '=' * 70))

        if total_removed == 0:
            self.stdout.write(self.style.SUCCESS('✓ No duplicate approvals found!'))
        else:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'✓ Found {total_removed} duplicate approval(s) in {vouchers_fixed} voucher(s)'
                    )
                )
                self.stdout.write(
                    self.style.WARNING('\nRun without --dry-run to actually remove them')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Successfully removed {total_removed} duplicate approval(s) from {vouchers_fixed} voucher(s)'
                    )
                )

        self.stdout.write(self.style.WARNING('=' * 70))