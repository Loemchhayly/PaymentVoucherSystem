"""
Management command to migrate existing attachments to PV number-based folder structure.
Usage: python manage.py migrate_attachments
"""
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db import transaction
from vouchers.models import VoucherAttachment
import os
import shutil


class Command(BaseCommand):
    help = 'Migrate existing attachments to PV number-based folder structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually moving files',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be moved'))
            self.stdout.write('')

        attachments = VoucherAttachment.objects.select_related('voucher').all()
        total = attachments.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No attachments to migrate'))
            return

        self.stdout.write(f'Found {total} attachment(s) to process')
        self.stdout.write('')

        migrated = 0
        skipped = 0
        errors = 0

        for attachment in attachments:
            voucher = attachment.voucher
            pv_number = voucher.pv_number or f"DRAFT-{voucher.id}"

            # Current file path
            old_path = attachment.file.name

            # New file path should be: voucher_attachments/{PV_NUMBER}/filename
            filename = os.path.basename(old_path)
            new_path = f'voucher_attachments/{pv_number}/{filename}'

            # Check if already in correct location
            if old_path.startswith(f'voucher_attachments/{pv_number}/'):
                self.stdout.write(
                    self.style.WARNING(f'[SKIP] {old_path} - Already in correct location')
                )
                skipped += 1
                continue

            # Check if old file exists
            if not default_storage.exists(old_path):
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] {old_path} - File not found')
                )
                errors += 1
                continue

            try:
                if not dry_run:
                    with transaction.atomic():
                        # Read the old file
                        old_file = default_storage.open(old_path, 'rb')
                        file_content = old_file.read()
                        old_file.close()

                        # Save to new location
                        default_storage.save(new_path, file_content)

                        # Update database record
                        attachment.file.name = new_path
                        attachment.save()

                        # Delete old file
                        default_storage.delete(old_path)

                self.stdout.write(
                    self.style.SUCCESS(f'[OK] {old_path} -> {new_path}')
                )
                migrated += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Failed to migrate {old_path}: {str(e)}')
                )
                errors += 1

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total: {total}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped}'))
        self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        self.stdout.write('=' * 70)

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN - No actual changes were made'))
            self.stdout.write('Run without --dry-run to perform the migration')
