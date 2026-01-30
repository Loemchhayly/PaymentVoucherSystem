from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from weasyprint import HTML
import os


class VoucherPDFGenerator:
    """Service for generating PDF vouchers with WeasyPrint"""

    @staticmethod
    def generate_pdf(voucher):
        """Generate PDF for a voucher."""
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

        # FIXED: Proper base_url for Windows
        media_root = os.path.abspath(settings.MEDIA_ROOT)

        # Convert Windows backslashes to forward slashes
        media_root = media_root.replace('\\', '/')

        # Ensure trailing slash
        if not media_root.endswith('/'):
            media_root += '/'

        # Use file:/// (three slashes) for absolute paths
        base_url = f"file:///{media_root}"

        # Generate PDF
        html = HTML(string=html_string, base_url=base_url)
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'PV_{voucher.pv_number}.pdf'
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


class FormPDFGenerator:
    """Service for generating PDF payment forms with WeasyPrint"""

    @staticmethod
    def generate_pdf(payment_form):
        """Generate PDF for a payment form."""
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

        # FIXED: Proper base_url for Windows
        media_root = os.path.abspath(settings.MEDIA_ROOT)

        # Convert Windows backslashes to forward slashes
        media_root = media_root.replace('\\', '/')

        # Ensure trailing slash
        if not media_root.endswith('/'):
            media_root += '/'

        # Use file:/// (three slashes) for absolute paths
        base_url = f"file:///{media_root}"

        # Generate PDF
        html = HTML(string=html_string, base_url=base_url)
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'PF_{payment_form.pf_number}.pdf'
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