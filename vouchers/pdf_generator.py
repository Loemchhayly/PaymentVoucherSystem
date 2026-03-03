from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from weasyprint import HTML
from pypdf import PdfWriter, PdfReader
from PIL import Image
import os
import io


class VoucherPDFGenerator:
    """Service for generating PDF vouchers with WeasyPrint"""

    @staticmethod
    def _convert_image_to_pdf(image_path):
        """
        Convert an image file to PDF bytes.
        Returns PDF bytes or None if conversion fails.
        """
        try:
            # Open image
            img = Image.open(image_path)

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create PDF in memory
            pdf_buffer = io.BytesIO()

            # Convert image to PDF using Pillow
            img.save(pdf_buffer, 'PDF', resolution=100.0)
            pdf_buffer.seek(0)

            return pdf_buffer.getvalue()
        except Exception as e:
            print(f"Error converting image to PDF: {e}")
            return None

    @staticmethod
    def _merge_attachments_to_pdf(main_pdf_bytes, attachments):
        """
        Merge attachment files into the main PDF.

        Args:
            main_pdf_bytes: The main voucher PDF as bytes
            attachments: QuerySet of VoucherAttachment objects

        Returns:
            Merged PDF as bytes
        """
        try:
            # Create PDF writer
            pdf_writer = PdfWriter()

            # Add main voucher pages
            main_pdf = PdfReader(io.BytesIO(main_pdf_bytes))
            for page in main_pdf.pages:
                pdf_writer.add_page(page)

            # Process each attachment
            for attachment in attachments:
                if not attachment.file:
                    continue

                file_path = attachment.file.path
                file_ext = attachment.get_file_extension().lower()

                # Skip the auto-generated PDF itself
                if attachment.filename.startswith('PV_') or attachment.filename.startswith('PF_'):
                    continue

                try:
                    # Handle images
                    if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif']:
                        image_pdf_bytes = VoucherPDFGenerator._convert_image_to_pdf(file_path)
                        if image_pdf_bytes:
                            image_pdf = PdfReader(io.BytesIO(image_pdf_bytes))
                            for page in image_pdf.pages:
                                pdf_writer.add_page(page)

                    # Handle PDF files
                    elif file_ext == 'pdf':
                        with open(file_path, 'rb') as pdf_file:
                            attachment_pdf = PdfReader(pdf_file)
                            for page in attachment_pdf.pages:
                                pdf_writer.add_page(page)

                    # Skip other file types (Word, Excel, etc.)
                    else:
                        print(f"Skipping unsupported file type: {file_ext} - {attachment.filename}")

                except Exception as e:
                    print(f"Error processing attachment {attachment.filename}: {e}")
                    continue

            # Write merged PDF to bytes
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)

            return output_buffer.getvalue()

        except Exception as e:
            print(f"Error merging attachments: {e}")
            # Return original PDF if merging fails
            return main_pdf_bytes

    @staticmethod
    def generate_pdf(voucher, include_attachments=True):
        """
        Generate PDF for a voucher.

        Args:
            voucher: PaymentVoucher instance
            include_attachments: If True, append user-uploaded attachments to PDF
        """
        # Use generate_pdf_file to get PDF with attachments
        pdf_bytes, filename = VoucherPDFGenerator.generate_pdf_file(voucher, include_attachments)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    @staticmethod
    def generate_pdf_preview(voucher):
        """Generate PDF preview (inline display)."""
        grand_total = voucher.calculate_grand_total()

        approval_history = voucher.approval_history.filter(
            action='APPROVE'
        ).order_by('timestamp')

        context = {
            'voucher': voucher,
            'grand_total': grand_total,
            'approval_history': approval_history,
            'line_items': voucher.line_items.all(),
        }

        html_string = render_to_string('vouchers/voucher_pdf.html', context)

        media_root = os.path.abspath(settings.MEDIA_ROOT)
        media_root = media_root.replace('\\', '/')

        if not media_root.endswith('/'):
            media_root += '/'

        base_url = f"file:///{media_root}"

        html = HTML(string=html_string, base_url=base_url)
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline'

        return response

    @staticmethod
    def generate_pdf_file(voucher, include_attachments=True):
        """
        Generate PDF file content for saving as attachment.

        Args:
            voucher: PaymentVoucher instance
            include_attachments: If True, append user-uploaded attachments to PDF

        Returns tuple of (pdf_bytes, filename)
        """
        grand_total = voucher.calculate_grand_total()

        approval_history = voucher.approval_history.filter(
            action='APPROVE'
        ).order_by('timestamp')

        context = {
            'voucher': voucher,
            'grand_total': grand_total,
            'approval_history': approval_history,
            'line_items': voucher.line_items.all(),
        }

        html_string = render_to_string('vouchers/voucher_pdf.html', context)

        media_root = os.path.abspath(settings.MEDIA_ROOT)
        media_root = media_root.replace('\\', '/')

        if not media_root.endswith('/'):
            media_root += '/'

        base_url = f"file:///{media_root}"

        html = HTML(string=html_string, base_url=base_url)
        pdf_bytes = html.write_pdf()

        # Merge user-uploaded attachments if requested
        if include_attachments:
            attachments = voucher.attachments.exclude(
                filename__startswith='PV_'
            ).order_by('uploaded_at')

            if attachments.exists():
                pdf_bytes = VoucherPDFGenerator._merge_attachments_to_pdf(pdf_bytes, attachments)

        filename = f'PV_{voucher.pv_number}.pdf'

        return pdf_bytes, filename


class FormPDFGenerator:
    """Service for generating PDF payment forms with WeasyPrint"""

    @staticmethod
    def _convert_image_to_pdf(image_path):
        """
        Convert an image file to PDF bytes.
        Returns PDF bytes or None if conversion fails.
        """
        try:
            # Open image
            img = Image.open(image_path)

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create PDF in memory
            pdf_buffer = io.BytesIO()

            # Convert image to PDF using Pillow
            img.save(pdf_buffer, 'PDF', resolution=100.0)
            pdf_buffer.seek(0)

            return pdf_buffer.getvalue()
        except Exception as e:
            print(f"Error converting image to PDF: {e}")
            return None

    @staticmethod
    def _merge_attachments_to_pdf(main_pdf_bytes, attachments):
        """
        Merge attachment files into the main PDF.

        Args:
            main_pdf_bytes: The main form PDF as bytes
            attachments: QuerySet of FormAttachment objects

        Returns:
            Merged PDF as bytes
        """
        try:
            # Create PDF writer
            pdf_writer = PdfWriter()

            # Add main form pages
            main_pdf = PdfReader(io.BytesIO(main_pdf_bytes))
            for page in main_pdf.pages:
                pdf_writer.add_page(page)

            # Process each attachment
            for attachment in attachments:
                if not attachment.file:
                    continue

                file_path = attachment.file.path
                file_ext = attachment.get_file_extension().lower()

                # Skip the auto-generated PDF itself
                if attachment.filename.startswith('PV_') or attachment.filename.startswith('PF_'):
                    continue

                try:
                    # Handle images
                    if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif']:
                        image_pdf_bytes = FormPDFGenerator._convert_image_to_pdf(file_path)
                        if image_pdf_bytes:
                            image_pdf = PdfReader(io.BytesIO(image_pdf_bytes))
                            for page in image_pdf.pages:
                                pdf_writer.add_page(page)

                    # Handle PDF files
                    elif file_ext == 'pdf':
                        with open(file_path, 'rb') as pdf_file:
                            attachment_pdf = PdfReader(pdf_file)
                            for page in attachment_pdf.pages:
                                pdf_writer.add_page(page)

                    # Skip other file types (Word, Excel, etc.)
                    else:
                        print(f"Skipping unsupported file type: {file_ext} - {attachment.filename}")

                except Exception as e:
                    print(f"Error processing attachment {attachment.filename}: {e}")
                    continue

            # Write merged PDF to bytes
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)

            return output_buffer.getvalue()

        except Exception as e:
            print(f"Error merging attachments: {e}")
            # Return original PDF if merging fails
            return main_pdf_bytes

    @staticmethod
    def generate_pdf(payment_form, include_attachments=True):
        """
        Generate PDF for a payment form.

        Args:
            payment_form: PaymentForm instance
            include_attachments: If True, append user-uploaded attachments to PDF
        """
        # Use generate_pdf_file to get PDF with attachments
        pdf_bytes, filename = FormPDFGenerator.generate_pdf_file(payment_form, include_attachments)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    @staticmethod
    def generate_pdf_preview(payment_form):
        """Generate PDF preview (inline display)."""
        grand_total = payment_form.calculate_grand_total()

        approval_history = payment_form.approval_history.filter(
            action='APPROVE'
        ).order_by('timestamp')

        context = {
            'payment_form': payment_form,
            'grand_total': grand_total,
            'approval_history': approval_history,
            'line_items': payment_form.line_items.all(),
            'now': timezone.now(),
        }

        html_string = render_to_string('vouchers/pf/form_pdf.html', context)

        media_root = os.path.abspath(settings.MEDIA_ROOT)
        media_root = media_root.replace('\\', '/')

        if not media_root.endswith('/'):
            media_root += '/'

        base_url = f"file:///{media_root}"

        html = HTML(string=html_string, base_url=base_url)
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline'

        return response

    @staticmethod
    def generate_pdf_file(payment_form, include_attachments=True):
        """
        Generate PDF file content for saving as attachment.

        Args:
            payment_form: PaymentForm instance
            include_attachments: If True, append user-uploaded attachments to PDF

        Returns tuple of (pdf_bytes, filename)
        """
        grand_total = payment_form.calculate_grand_total()

        approval_history = payment_form.approval_history.filter(
            action='APPROVE'
        ).order_by('timestamp')

        context = {
            'payment_form': payment_form,
            'grand_total': grand_total,
            'approval_history': approval_history,
            'line_items': payment_form.line_items.all(),
            'now': timezone.now(),
        }

        html_string = render_to_string('vouchers/pf/form_pdf.html', context)

        media_root = os.path.abspath(settings.MEDIA_ROOT)
        media_root = media_root.replace('\\', '/')

        if not media_root.endswith('/'):
            media_root += '/'

        base_url = f"file:///{media_root}"

        html = HTML(string=html_string, base_url=base_url)
        pdf_bytes = html.write_pdf()

        # Merge user-uploaded attachments if requested
        if include_attachments:
            attachments = payment_form.attachments.exclude(
                filename__startswith='PF_'
            ).order_by('uploaded_at')

            if attachments.exists():
                pdf_bytes = FormPDFGenerator._merge_attachments_to_pdf(pdf_bytes, attachments)

        filename = f'PF_{payment_form.pf_number}.pdf'

        return pdf_bytes, filename