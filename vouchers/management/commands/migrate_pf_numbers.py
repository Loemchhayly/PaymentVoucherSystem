"""
Management command to migrate PF numbers from old format (YYMM-PF-NNNN) to new format (YYMM-NNNN).
Usage: python manage.py migrate_pf_numbers
"""
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from vouchers.models import PaymentForm, FormAttachment
import os


class Command(BaseCommand):
    help = 'Migrate PF numbers from old format (YYMM-PF-NNNN) to new format (YYMM-NNNN)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually updating records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')

        # Find all PaymentForms with old format PF numbers
        old_format_forms = PaymentForm.objects.filter(
            pf_number__contains='-PF-'
        ).order_by('id')

        total = old_format_forms.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No PF numbers to migrate'))
            return

        self.stdout.write(f'Found {total} PF number(s) to migrate')
        self.stdout.write('')

        migrated = 0
        errors = 0

        for form in old_format_forms:
            old_pf_number = form.pf_number

            # Convert format: 2601-PF-0001 -> 2601-0001
            parts = old_pf_number.split('-')
            if len(parts) == 3 and parts[1] == 'PF':
                new_pf_number = f"{parts[0]}-{parts[2]}"

                try:
                    if not dry_run:
                        with transaction.atomic():
                            # Update the PF number
                            form.pf_number = new_pf_number
                            form.save()

                            # Update attachment folder paths
                            attachments = FormAttachment.objects.filter(payment_form=form)
                            for attachment in attachments:
                                old_path = attachment.file.name

                                # Check if path contains old PF number
                                if old_pf_number in old_path:
                                    # Replace old PF number with new one in path
                                    new_path = old_path.replace(old_pf_number, new_pf_number)

                                    # Only migrate if file exists
                                    if default_storage.exists(old_path):
                                        # Read the old file
                                        with default_storage.open(old_path, 'rb') as old_file:
                                            file_content = old_file.read()

                                        # Save to new location
                                        default_storage.save(new_path, ContentFile(file_content))

                                        # Update database record
                                        attachment.file.name = new_path
                                        attachment.save()

                                        # Delete old file
                                        default_storage.delete(old_path)

                                        self.stdout.write(
                                            self.style.SUCCESS(f'  [ATTACHMENT] {old_path} -> {new_path}')
                                        )

                    self.stdout.write(
                        self.style.SUCCESS(f'[OK] ID: {form.id}, {old_pf_number} -> {new_pf_number} ({form.payee_name})')
                    )
                    migrated += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'[ERROR] Failed to migrate {old_pf_number}: {str(e)}')
                    )
                    errors += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'[SKIP] {old_pf_number} - Invalid format')
                )

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total: {total}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated}'))
        self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
        self.stdout.write('=' * 70)

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN - No actual changes were made'))
            self.stdout.write('Run without --dry-run to perform the migration')
