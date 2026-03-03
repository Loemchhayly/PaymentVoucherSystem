"""
Management command to regenerate existing approved PDFs with user attachments embedded.
This updates old PDFs to include all user-uploaded files (images, PDFs) within the main PDF.

Usage:
    python manage.py regenerate_pdfs_with_attachments
    python manage.py regenerate_pdfs_with_attachments --dry-run
    python manage.py regenerate_pdfs_with_attachments --vouchers-only
    python manage.py regenerate_pdfs_with_attachments --forms-only
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from vouchers.models import PaymentVoucher, PaymentForm, VoucherAttachment, FormAttachment
from vouchers.pdf_generator import VoucherPDFGenerator, FormPDFGenerator
from django.core.files.base import ContentFile

User = get_user_model()


class Command(BaseCommand):
    help = 'Regenerate existing approved PDFs with user attachments embedded'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually regenerating PDFs',
        )
        parser.add_argument(
            '--vouchers-only',
            action='store_true',
            help='Only process Payment Vouchers (PV)',
        )
        parser.add_argument(
            '--forms-only',
            action='store_true',
            help='Only process Payment Forms (PF)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        vouchers_only = options['vouchers_only']
        forms_only = options['forms_only']

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No PDFs will be regenerated'))
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write('')

        # Get system user for upload attribution (use first superuser or first user)
        system_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not system_user:
            self.stdout.write(self.style.ERROR('No users found in system. Cannot proceed.'))
            return

        self.stdout.write(f'Using system user: {system_user.username} for upload attribution')
        self.stdout.write('')

        pv_processed = 0
        pv_skipped = 0
        pv_errors = 0

        pf_processed = 0
        pf_skipped = 0
        pf_errors = 0

        # Process Payment Vouchers (PV)
        if not forms_only:
            self.stdout.write(self.style.HTTP_INFO('REGENERATING PAYMENT VOUCHER PDFs WITH ATTACHMENTS'))
            self.stdout.write('-' * 70)

            # Find approved vouchers that have existing auto-generated PDFs
            approved_vouchers = PaymentVoucher.objects.filter(status='APPROVED')
            total_pv = approved_vouchers.count()

            if total_pv == 0:
                self.stdout.write(self.style.WARNING('No approved Payment Vouchers found'))
            else:
                self.stdout.write(f'Found {total_pv} approved Payment Voucher(s)')
                self.stdout.write('')

                for voucher in approved_vouchers:
                    pdf_filename = f'PV_{voucher.pv_number}.pdf'

                    # Check if voucher has the auto-generated PDF
                    existing_pdf = voucher.attachments.filter(filename=pdf_filename).first()

                    if not existing_pdf:
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {voucher.pv_number} - No existing PDF found')
                        )
                        pv_skipped += 1
                        continue

                    # Check if voucher has other attachments to embed
                    user_attachments = voucher.attachments.exclude(filename=pdf_filename)
                    if not user_attachments.exists():
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {voucher.pv_number} - No user attachments to embed')
                        )
                        pv_skipped += 1
                        continue

                    # Regenerate PDF with attachments
                    try:
                        if not dry_run:
                            # Delete old PDF attachment
                            old_file_path = existing_pdf.file.path
                            existing_pdf.delete()

                            # Try to delete the physical file
                            try:
                                import os
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                            except:
                                pass

                            # Generate new PDF with attachments
                            pdf_bytes, filename = VoucherPDFGenerator.generate_pdf_file(
                                voucher,
                                include_attachments=True
                            )

                            # Create new attachment
                            attachment = VoucherAttachment(
                                voucher=voucher,
                                filename=filename,
                                file_size=len(pdf_bytes),
                                uploaded_by=system_user
                            )
                            attachment.file.save(filename, ContentFile(pdf_bytes), save=True)

                        attachment_count = user_attachments.count()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'[OK] {voucher.pv_number} - Regenerated with {attachment_count} attachment(s)'
                            )
                        )
                        pv_processed += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'[ERROR] {voucher.pv_number} - {str(e)}')
                        )
                        pv_errors += 1

            self.stdout.write('')

        # Process Payment Forms (PF)
        if not vouchers_only:
            self.stdout.write(self.style.HTTP_INFO('REGENERATING PAYMENT FORM PDFs WITH ATTACHMENTS'))
            self.stdout.write('-' * 70)

            # Find approved forms that have existing auto-generated PDFs
            approved_forms = PaymentForm.objects.filter(status='APPROVED')
            total_pf = approved_forms.count()

            if total_pf == 0:
                self.stdout.write(self.style.WARNING('No approved Payment Forms found'))
            else:
                self.stdout.write(f'Found {total_pf} approved Payment Form(s)')
                self.stdout.write('')

                for form in approved_forms:
                    pdf_filename = f'PF_{form.pf_number}.pdf'

                    # Check if form has the auto-generated PDF
                    existing_pdf = form.attachments.filter(filename=pdf_filename).first()

                    if not existing_pdf:
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {form.pf_number} - No existing PDF found')
                        )
                        pf_skipped += 1
                        continue

                    # Check if form has other attachments to embed
                    user_attachments = form.attachments.exclude(filename=pdf_filename)
                    if not user_attachments.exists():
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {form.pf_number} - No user attachments to embed')
                        )
                        pf_skipped += 1
                        continue

                    # Regenerate PDF with attachments
                    try:
                        if not dry_run:
                            # Delete old PDF attachment
                            old_file_path = existing_pdf.file.path
                            existing_pdf.delete()

                            # Try to delete the physical file
                            try:
                                import os
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                            except:
                                pass

                            # Generate new PDF with attachments
                            pdf_bytes, filename = FormPDFGenerator.generate_pdf_file(
                                form,
                                include_attachments=True
                            )

                            # Create new attachment
                            attachment = FormAttachment(
                                payment_form=form,
                                filename=filename,
                                file_size=len(pdf_bytes),
                                uploaded_by=system_user
                            )
                            attachment.file.save(filename, ContentFile(pdf_bytes), save=True)

                        attachment_count = user_attachments.count()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'[OK] {form.pf_number} - Regenerated with {attachment_count} attachment(s)'
                            )
                        )
                        pf_processed += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'[ERROR] {form.pf_number} - {str(e)}')
                        )
                        pf_errors += 1

            self.stdout.write('')

        # Summary
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.HTTP_INFO('SUMMARY'))
        self.stdout.write('=' * 70)

        if not forms_only:
            self.stdout.write(f'Payment Vouchers (PV):')
            self.stdout.write(self.style.SUCCESS(f'  + Regenerated: {pv_processed}'))
            self.stdout.write(self.style.WARNING(f'  - Skipped: {pv_skipped}'))
            if pv_errors > 0:
                self.stdout.write(self.style.ERROR(f'  x Errors: {pv_errors}'))
            self.stdout.write('')

        if not vouchers_only:
            self.stdout.write(f'Payment Forms (PF):')
            self.stdout.write(self.style.SUCCESS(f'  + Regenerated: {pf_processed}'))
            self.stdout.write(self.style.WARNING(f'  - Skipped: {pf_skipped}'))
            if pf_errors > 0:
                self.stdout.write(self.style.ERROR(f'  x Errors: {pf_errors}'))
            self.stdout.write('')

        total_processed = pv_processed + pf_processed
        total_errors = pv_errors + pf_errors

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('DRY RUN - No actual PDFs were regenerated'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to regenerate PDFs'))
            self.stdout.write(self.style.WARNING('=' * 70))
        elif total_errors == 0 and total_processed > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully regenerated {total_processed} PDF(s) with attachments'))
        elif total_errors > 0:
            self.stdout.write(self.style.ERROR(f'Completed with {total_errors} error(s)'))
