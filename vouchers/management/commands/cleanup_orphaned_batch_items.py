"""
Management command to clean up orphaned batch items
(batch items that reference deleted vouchers or forms)

Usage: python manage.py cleanup_orphaned_batch_items
"""
from django.core.management.base import BaseCommand
from vouchers.models import BatchVoucherItem, BatchFormItem, PaymentVoucher, PaymentForm


class Command(BaseCommand):
    help = 'Clean up orphaned batch items (items referencing deleted documents)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Checking for orphaned batch items...'))

        # Check voucher items
        orphaned_voucher_items = []
        for item in BatchVoucherItem.objects.all():
            try:
                # Check if voucher still exists
                if not item.voucher_id or not PaymentVoucher.objects.filter(id=item.voucher_id).exists():
                    orphaned_voucher_items.append(item)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking voucher item {item.id}: {e}'))
                orphaned_voucher_items.append(item)

        # Check form items
        orphaned_form_items = []
        for item in BatchFormItem.objects.all():
            try:
                # Check if payment form still exists
                if not item.payment_form_id or not PaymentForm.objects.filter(id=item.payment_form_id).exists():
                    orphaned_form_items.append(item)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking form item {item.id}: {e}'))
                orphaned_form_items.append(item)

        total_orphaned = len(orphaned_voucher_items) + len(orphaned_form_items)

        if total_orphaned == 0:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned batch items found. Database is clean!'))
            return

        self.stdout.write(self.style.WARNING(f'\nFound {total_orphaned} orphaned batch item(s):'))
        self.stdout.write(f'  - {len(orphaned_voucher_items)} orphaned voucher items')
        self.stdout.write(f'  - {len(orphaned_form_items)} orphaned form items')

        # Ask for confirmation
        confirm = input('\nDo you want to delete these orphaned items? (yes/no): ')

        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Operation cancelled.'))
            return

        # Delete orphaned items
        deleted_voucher_count = 0
        for item in orphaned_voucher_items:
            batch_id = item.batch_id
            item.delete()
            deleted_voucher_count += 1
            self.stdout.write(f'  - Deleted orphaned voucher item from batch #{batch_id}')

        deleted_form_count = 0
        for item in orphaned_form_items:
            batch_id = item.batch_id
            item.delete()
            deleted_form_count += 1
            self.stdout.write(f'  - Deleted orphaned form item from batch #{batch_id}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Successfully deleted {deleted_voucher_count + deleted_form_count} orphaned batch item(s)!'
        ))
        self.stdout.write(self.style.SUCCESS('Database cleanup complete.'))
