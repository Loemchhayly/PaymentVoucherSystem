"""
Django management command to check batch integrity
Usage: python manage.py check_batch_integrity
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from vouchers.models import (
    BatchVoucherItem, BatchFormItem,
    PaymentVoucher, PaymentForm,
    SignatureBatch
)


class Command(BaseCommand):
    help = 'Check for orphaned batch items and show detailed report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix orphaned items (delete them)',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.WARNING('CHECKING BATCH INTEGRITY'))
        self.stdout.write('=' * 70)

        # Get all existing voucher and form IDs
        existing_voucher_ids = set(PaymentVoucher.objects.values_list('id', flat=True))
        existing_form_ids = set(PaymentForm.objects.values_list('id', flat=True))

        self.stdout.write(f'\nDatabase status:')
        self.stdout.write(f'  Payment Vouchers: {len(existing_voucher_ids)}')
        self.stdout.write(f'  Payment Forms: {len(existing_form_ids)}')

        # Check voucher batch items
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('VOUCHER BATCH ITEMS')
        self.stdout.write('-' * 70)

        voucher_items = BatchVoucherItem.objects.select_related('batch')
        orphaned_vouchers = []

        for item in voucher_items:
            if item.voucher_id not in existing_voucher_ids:
                orphaned_vouchers.append({
                    'item': item,
                    'voucher_id': item.voucher_id,
                    'batch': item.batch
                })

        if orphaned_vouchers:
            self.stdout.write(self.style.ERROR(
                f'\n⚠ FOUND {len(orphaned_vouchers)} ORPHANED VOUCHER ITEM(S):'
            ))
            for orphan in orphaned_vouchers:
                self.stdout.write(f"\n  Batch Item #{orphan['item'].id}:")
                self.stdout.write(f"    - References voucher_id: {orphan['voucher_id']} (DELETED)")
                self.stdout.write(f"    - In batch: {orphan['batch'].batch_number} (ID: {orphan['batch'].id})")
                self.stdout.write(f"    - Batch status: {orphan['batch'].status}")
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No orphaned voucher items'))

        # Check form batch items
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('FORM BATCH ITEMS')
        self.stdout.write('-' * 70)

        form_items = BatchFormItem.objects.select_related('batch')
        orphaned_forms = []

        for item in form_items:
            if item.payment_form_id not in existing_form_ids:
                orphaned_forms.append({
                    'item': item,
                    'form_id': item.payment_form_id,
                    'batch': item.batch
                })

        if orphaned_forms:
            self.stdout.write(self.style.ERROR(
                f'\n⚠ FOUND {len(orphaned_forms)} ORPHANED FORM ITEM(S):'
            ))
            for orphan in orphaned_forms:
                self.stdout.write(f"\n  Batch Item #{orphan['item'].id}:")
                self.stdout.write(f"    - References form_id: {orphan['form_id']} (DELETED)")
                self.stdout.write(f"    - In batch: {orphan['batch'].batch_number} (ID: {orphan['batch'].id})")
                self.stdout.write(f"    - Batch status: {orphan['batch'].status}")
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No orphaned form items'))

        # Summary
        total_orphans = len(orphaned_vouchers) + len(orphaned_forms)

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('SUMMARY')
        self.stdout.write('=' * 70)

        if total_orphans > 0:
            self.stdout.write(self.style.ERROR(f'\n⚠ TOTAL ORPHANED ITEMS: {total_orphans}'))
            self.stdout.write(f'  - Orphaned voucher items: {len(orphaned_vouchers)}')
            self.stdout.write(f'  - Orphaned form items: {len(orphaned_forms)}')

            # Show affected batches
            affected_batches = set()
            for orphan in orphaned_vouchers:
                affected_batches.add(orphan['batch'].batch_number)
            for orphan in orphaned_forms:
                affected_batches.add(orphan['batch'].batch_number)

            self.stdout.write(f'\nAffected batches: {", ".join(sorted(affected_batches))}')

            # Auto-fix if requested
            if options['fix']:
                self.stdout.write('\n' + '-' * 70)
                self.stdout.write(self.style.WARNING('FIXING ORPHANED ITEMS...'))
                self.stdout.write('-' * 70)

                deleted_count = 0
                for orphan in orphaned_vouchers:
                    orphan['item'].delete()
                    deleted_count += 1
                    self.stdout.write(f"  ✓ Deleted orphaned voucher item #{orphan['item'].id}")

                for orphan in orphaned_forms:
                    orphan['item'].delete()
                    deleted_count += 1
                    self.stdout.write(f"  ✓ Deleted orphaned form item #{orphan['item'].id}")

                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Successfully deleted {deleted_count} orphaned item(s)!'
                ))
            else:
                self.stdout.write('\nTo fix automatically, run:')
                self.stdout.write(self.style.WARNING('  python manage.py check_batch_integrity --fix'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ NO ORPHANED ITEMS FOUND'))
            self.stdout.write('All batch items reference valid documents.')
