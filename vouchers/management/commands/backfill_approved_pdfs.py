"""
Management command to automatically attach PDFs to all approved vouchers/forms.
This backfills existing APPROVED documents that don't have auto-generated PDFs.

Usage:
    python manage.py backfill_approved_pdfs
    python manage.py backfill_approved_pdfs --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from vouchers.models import PaymentVoucher, PaymentForm, VoucherAttachment, FormAttachment
from vouchers.pdf_generator import VoucherPDFGenerator, FormPDFGenerator
from django.core.files.base import ContentFile

User = get_user_model()


class Command(BaseCommand):
    help = 'Backfill auto-generated PDFs for all approved vouchers and forms'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually creating PDFs',
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
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No PDFs will be created'))
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
            self.stdout.write(self.style.HTTP_INFO('PROCESSING PAYMENT VOUCHERS (PV)'))
            self.stdout.write('-' * 70)

            approved_vouchers = PaymentVoucher.objects.filter(status='APPROVED')
            total_pv = approved_vouchers.count()

            if total_pv == 0:
                self.stdout.write(self.style.WARNING('No approved Payment Vouchers found'))
            else:
                self.stdout.write(f'Found {total_pv} approved Payment Voucher(s)')
                self.stdout.write('')

                for voucher in approved_vouchers:
                    pdf_filename = f'PV_{voucher.pv_number}.pdf'

                    # Check if PDF already exists
                    if voucher.attachments.filter(filename=pdf_filename).exists():
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {voucher.pv_number} - PDF already exists')
                        )
                        pv_skipped += 1
                        continue

                    # Generate and attach PDF
                    try:
                        if not dry_run:
                            pdf_bytes, filename = VoucherPDFGenerator.generate_pdf_file(voucher)

                            attachment = VoucherAttachment(
                                voucher=voucher,
                                filename=filename,
                                file_size=len(pdf_bytes),
                                uploaded_by=system_user
                            )
                            attachment.file.save(filename, ContentFile(pdf_bytes), save=True)

                        self.stdout.write(
                            self.style.SUCCESS(f'[OK] {voucher.pv_number} - PDF attached ({pdf_filename})')
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
            self.stdout.write(self.style.HTTP_INFO('PROCESSING PAYMENT FORMS (PF)'))
            self.stdout.write('-' * 70)

            approved_forms = PaymentForm.objects.filter(status='APPROVED')
            total_pf = approved_forms.count()

            if total_pf == 0:
                self.stdout.write(self.style.WARNING('No approved Payment Forms found'))
            else:
                self.stdout.write(f'Found {total_pf} approved Payment Form(s)')
                self.stdout.write('')

                for form in approved_forms:
                    pdf_filename = f'PF_{form.pf_number}.pdf'

                    # Check if PDF already exists
                    if form.attachments.filter(filename=pdf_filename).exists():
                        self.stdout.write(
                            self.style.WARNING(f'[SKIP] {form.pf_number} - PDF already exists')
                        )
                        pf_skipped += 1
                        continue

                    # Generate and attach PDF
                    try:
                        if not dry_run:
                            pdf_bytes, filename = FormPDFGenerator.generate_pdf_file(form)

                            attachment = FormAttachment(
                                payment_form=form,
                                filename=filename,
                                file_size=len(pdf_bytes),
                                uploaded_by=system_user
                            )
                            attachment.file.save(filename, ContentFile(pdf_bytes), save=True)

                        self.stdout.write(
                            self.style.SUCCESS(f'[OK] {form.pf_number} - PDF attached ({pdf_filename})')
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
            self.stdout.write(self.style.SUCCESS(f'  + Processed: {pv_processed}'))
            self.stdout.write(self.style.WARNING(f'  - Skipped: {pv_skipped}'))
            if pv_errors > 0:
                self.stdout.write(self.style.ERROR(f'  x Errors: {pv_errors}'))
            self.stdout.write('')

        if not vouchers_only:
            self.stdout.write(f'Payment Forms (PF):')
            self.stdout.write(self.style.SUCCESS(f'  + Processed: {pf_processed}'))
            self.stdout.write(self.style.WARNING(f'  - Skipped: {pf_skipped}'))
            if pf_errors > 0:
                self.stdout.write(self.style.ERROR(f'  x Errors: {pf_errors}'))
            self.stdout.write('')

        total_processed = pv_processed + pf_processed
        total_errors = pv_errors + pf_errors

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('DRY RUN - No actual PDFs were created'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to create PDFs'))
            self.stdout.write(self.style.WARNING('=' * 70))
        elif total_errors == 0 and total_processed > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully processed {total_processed} document(s)'))
        elif total_errors > 0:
            self.stdout.write(self.style.ERROR(f'Completed with {total_errors} error(s)'))
