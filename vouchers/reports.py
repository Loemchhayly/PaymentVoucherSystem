"""
Advanced Reporting System for Payment Vouchers and Forms
Supports Excel and PDF exports with comprehensive filters
"""
from django.http import HttpResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from io import BytesIO
from decimal import Decimal

# Excel
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from .models import PaymentVoucher, PaymentForm, Department
from accounts.models import User


class ReportGenerator:
    """Main report generator class with advanced filtering"""

    def __init__(self, filters=None):
        """Initialize with optional filters"""
        self.filters = filters or {}
        self.vouchers = None
        self.forms = None

    def apply_filters(self):
        """Apply filters to querysets"""
        # Start with all vouchers and forms
        vouchers_qs = PaymentVoucher.objects.all()
        forms_qs = PaymentForm.objects.all()

        # Date range filter
        date_from = self.filters.get('date_from')
        date_to = self.filters.get('date_to')

        if date_from:
            vouchers_qs = vouchers_qs.filter(payment_date__gte=date_from)
            forms_qs = forms_qs.filter(payment_date__gte=date_from)

        if date_to:
            vouchers_qs = vouchers_qs.filter(payment_date__lte=date_to)
            forms_qs = forms_qs.filter(payment_date__lte=date_to)

        # Status filter - default to show documents after L2 (Account Supervisor) approval
        # This includes: PENDING_L3, PENDING_L4, PENDING_L5, and APPROVED
        status = self.filters.get('status')
        if status and status != 'ALL':
            vouchers_qs = vouchers_qs.filter(status=status)
            forms_qs = forms_qs.filter(status=status)
        else:
            # If no status filter specified, show documents after L2 approval
            # (PENDING_L3 onwards means L2 has already approved)
            allowed_statuses = ['PENDING_L3', 'PENDING_L4', 'PENDING_L5', 'APPROVED']
            vouchers_qs = vouchers_qs.filter(status__in=allowed_statuses)
            forms_qs = forms_qs.filter(status__in=allowed_statuses)

        # Creator filter
        creator_id = self.filters.get('creator')
        if creator_id:
            vouchers_qs = vouchers_qs.filter(created_by_id=creator_id)
            forms_qs = forms_qs.filter(created_by_id=creator_id)

        # Department filter
        department_name = self.filters.get('department')
        if department_name:
            vouchers_qs = vouchers_qs.filter(line_items__department__name=department_name).distinct()
            forms_qs = forms_qs.filter(line_items__department__name=department_name).distinct()

        # Payee filter
        payee_name = self.filters.get('payee_name')
        if payee_name:
            vouchers_qs = vouchers_qs.filter(payee_name__icontains=payee_name)
            forms_qs = forms_qs.filter(payee_name__icontains=payee_name)

        # Document type filter
        doc_type = self.filters.get('doc_type', 'ALL')
        if doc_type == 'PV':
            forms_qs = PaymentForm.objects.none()
        elif doc_type == 'PF':
            vouchers_qs = PaymentVoucher.objects.none()

        self.vouchers = vouchers_qs.select_related('created_by').prefetch_related('line_items')
        self.forms = forms_qs.select_related('created_by').prefetch_related('line_items')

        return self

    def get_summary_stats(self):
        """Calculate summary statistics"""
        if self.vouchers is None or self.forms is None:
            self.apply_filters()

        stats = {
            'total_vouchers': self.vouchers.count(),
            'total_forms': self.forms.count(),
            'total_documents': self.vouchers.count() + self.forms.count(),
            'by_status': {},
            'by_currency': {'USD': Decimal('0'), 'KHR': Decimal('0'), 'THB': Decimal('0')},
        }

        # Count by status
        for status_code, status_label in PaymentVoucher.STATUS_CHOICES:
            count = self.vouchers.filter(status=status_code).count() + self.forms.filter(status=status_code).count()
            if count > 0:
                stats['by_status'][status_label] = count

        # Calculate totals by currency
        for voucher in self.vouchers:
            totals = voucher.calculate_grand_total()
            for currency, amount in totals.items():
                stats['by_currency'][currency] += amount

        for form in self.forms:
            totals = form.calculate_grand_total()
            for currency, amount in totals.items():
                stats['by_currency'][currency] += amount

        return stats

    def export_to_excel(self):
        """Export filtered data to Excel matching the exact template format"""
        if self.vouchers is None or self.forms is None:
            self.apply_filters()

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Payment Voucher Summary"

        # ===========================================================================
        # SET COLUMN WIDTHS (UPDATED WITH TRANSFER ACCOUNT COLUMN)
        # ===========================================================================
        column_widths = {
            'A': 3.71,   # No
            'B': 15.14,  # PV No
            'C': 25.0,   # Supplier
            'D': 50.0,   # Description
            'E': 18.0,   # Amount
            'F': 28.0,   # Transfer Account (Company)
            'G': 25.0,   # Account Name (Payee)
            'H': 20.0,   # Account Number (Payee)
            'I': 20.0    # Remark
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        # ===========================================================================
        # DEFINE STYLES
        # ===========================================================================
        header_font = Font(name='Calibri', size=11, bold=True, color='000000')
        company_font = Font(name='Calibri', size=14, bold=True, color='000000')
        title_font = Font(name='Calibri', size=13, bold=True, color='000000')
        data_font = Font(name='Calibri', size=11, color='000000')

        header_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')

        border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )

        center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        right_alignment = Alignment(horizontal='right', vertical='center')

        # ===========================================================================
        # ROW 1: COMPANY NAME
        # ===========================================================================
        ws.merge_cells('A1:I1')
        company_cell = ws['A1']
        company_cell.value = "Phat Phnom Penh  Co.,LTD  (Garden City Water Park)"
        company_cell.font = company_font
        company_cell.alignment = center_alignment

        # ===========================================================================
        # ROW 2: TITLE
        # ===========================================================================
        ws.merge_cells('A2:I2')
        title_cell = ws['A2']
        title_cell.value = "Summary Payment Voucher"
        title_cell.font = title_font
        title_cell.alignment = center_alignment

        # ===========================================================================
        # ROW 3: DATE
        # ===========================================================================
        # "Date" label (Column H)
        date_label_cell = ws['H3']
        date_label_cell.value = "Date"
        date_label_cell.font = header_font
        date_label_cell.alignment = right_alignment

        # Current date (Column I)
        date_cell = ws['I3']
        date_cell.value = timezone.now().strftime('%Y-%m-%d')
        date_cell.font = data_font
        date_cell.alignment = left_alignment

        # ===========================================================================
        # ROW 4: REPORT DESCRIPTION
        # ===========================================================================
        ws.merge_cells('A4:I4')
        transfer_cell = ws['A4']
        transfer_cell.value = "Payment Vouchers Report - Grouped by Transfer Account"
        transfer_cell.font = Font(name='Calibri', size=11, bold=False)
        transfer_cell.alignment = left_alignment

        # ===========================================================================
        # PREPARE AND SORT DATA BY TRANSFER ACCOUNT
        # ===========================================================================
        all_documents = list(self.vouchers) + list(self.forms)

        # Sort by: 1) company_bank_account, 2) payment_date
        def get_sort_key(doc):
            if doc.company_bank_account:
                return (0, doc.company_bank_account.bank, doc.payment_date)
            else:
                return (1, 'ZZZ_No Account', doc.payment_date)

        all_documents.sort(key=get_sort_key)

        # ===========================================================================
        # ROWS 5-6: COLUMN HEADERS (WITH MERGED CELLS)
        # ===========================================================================
        # Merge cells for headers
        merge_ranges = [
            'A5:A6',  # No
            'B5:B6',  # PV No
            'C5:C6',  # Supplier
            'D5:D6',  # Description
            'E5:E6',  # Amount
            'F5:F6',  # Transfer Account (Company)
            'G5:H5',  # Receiver Bank Account (merged horizontally)
            'I5:I6'   # Remark
        ]

        for merge_range in merge_ranges:
            ws.merge_cells(merge_range)

        # Row 5 headers
        headers_row5 = [
            ('A5', 'No'),
            ('B5', 'PV No.'),
            ('C5', 'Supplier'),
            ('D5', 'Description'),
            ('E5', 'Amount'),
            ('F5', 'Transfer Account'),
            ('G5', 'Receiver Bank Account'),
            ('I5', 'Remark')
        ]

        for cell_ref, value in headers_row5:
            cell = ws[cell_ref]
            cell.value = value
            cell.font = header_font
            cell.alignment = center_alignment
            cell.fill = header_fill
            cell.border = border

        # Row 6 sub-headers
        headers_row6 = [
            ('G6', 'Account Name'),
            ('H6', 'Account Number')
        ]

        for cell_ref, value in headers_row6:
            cell = ws[cell_ref]
            cell.value = value
            cell.font = header_font
            cell.alignment = center_alignment
            cell.fill = header_fill
            cell.border = border

        # Apply borders to all header cells
        for row in [5, 6]:
            for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
                cell = ws[f'{col}{row}']
                if not cell.border.left.style:
                    cell.border = border
                    cell.fill = header_fill

        header_row = 7

        # ===========================================================================
        # DATA ROWS WITH GROUPING BY TRANSFER ACCOUNT
        # ===========================================================================
        row = header_row
        total_amount = Decimal('0')
        idx = 0
        current_bank = None
        bank_subtotal = Decimal('0')

        # Loop through all documents (sorted by transfer account)
        for doc in all_documents:
            idx += 1

            # Determine if this is a voucher or form
            is_voucher = hasattr(doc, 'pv_number')
            doc_number = doc.pv_number if is_voucher else doc.pf_number

            # Get transfer account (company account)
            if doc.company_bank_account:
                transfer_account = f"{doc.company_bank_account.bank}"
                transfer_account_full = f"{doc.company_bank_account.company_name} - {doc.company_bank_account.account_number} ({doc.company_bank_account.currency}) {doc.company_bank_account.bank}"
            else:
                transfer_account = "No Transfer Account"
                transfer_account_full = "No Transfer Account Specified"

            # Check if we need to add a section header (transfer account changed)
            if current_bank != transfer_account:
                # Add subtotal for previous bank (if any)
                if current_bank is not None and bank_subtotal > 0:
                    # Subtotal row
                    subtotal_cell = ws.cell(row=row, column=4)
                    subtotal_cell.value = f"Subtotal - {current_bank}:"
                    subtotal_cell.font = Font(name='Calibri', size=11, bold=True)
                    subtotal_cell.alignment = right_alignment
                    subtotal_cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
                    subtotal_cell.border = border

                    subtotal_amount_cell = ws.cell(row=row, column=5)
                    subtotal_amount_cell.value = float(bank_subtotal)
                    subtotal_amount_cell.font = Font(name='Calibri', size=11, bold=True)
                    subtotal_amount_cell.alignment = right_alignment
                    subtotal_amount_cell.number_format = '#,##0.00'
                    subtotal_amount_cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
                    subtotal_amount_cell.border = border

                    # Apply borders to other cells in subtotal row
                    for col in [1, 2, 3, 6, 7, 8, 9]:
                        cell = ws.cell(row=row, column=col)
                        cell.border = border
                        cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')

                    row += 1
                    bank_subtotal = Decimal('0')

                # Section header
                ws.merge_cells(f'A{row}:I{row}')
                section_cell = ws.cell(row=row, column=1)
                section_cell.value = f"═══ Transfer Account: {transfer_account_full} ═══"
                section_cell.font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
                section_cell.alignment = center_alignment
                section_cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                section_cell.border = border

                row += 1
                current_bank = transfer_account

            # Calculate totals
            totals = doc.calculate_grand_total()

            # Combine all line item descriptions (with newlines)
            descriptions = [item.description for item in doc.line_items.all()]
            combined_description = '\n'.join(descriptions) if descriptions else ''

            # Calculate USD amount
            amount = totals.get('USD', Decimal('0'))
            total_amount += amount
            bank_subtotal += amount

            # Get PAYEE's bank account information (recipient, not company account)
            account_name = doc.bank_name or ''  # Payee's account holder name
            account_number = doc.bank_account_number or ''  # Payee's account number

            # Column A: Sequential number
            cell_a = ws.cell(row=row, column=1)
            cell_a.value = idx
            cell_a.font = data_font
            cell_a.alignment = center_alignment
            cell_a.border = border

            # Column B: PV/PF Number
            cell_b = ws.cell(row=row, column=2)
            cell_b.value = doc_number or 'DRAFT'
            cell_b.font = data_font
            cell_b.alignment = left_alignment
            cell_b.border = border

            # Column C: Supplier/Payee
            cell_c = ws.cell(row=row, column=3)
            cell_c.value = doc.payee_name
            cell_c.font = data_font
            cell_c.alignment = left_alignment
            cell_c.border = border

            # Column D: Description
            cell_d = ws.cell(row=row, column=4)
            cell_d.value = combined_description
            cell_d.font = data_font
            cell_d.alignment = left_alignment
            cell_d.border = border

            # Column E: Amount (right-aligned, formatted)
            cell_e = ws.cell(row=row, column=5)
            cell_e.value = float(amount)
            cell_e.font = data_font
            cell_e.alignment = right_alignment
            cell_e.border = border
            cell_e.number_format = '#,##0.00'

            # Column F: Transfer Account (Company Bank)
            cell_f = ws.cell(row=row, column=6)
            cell_f.value = transfer_account
            cell_f.font = data_font
            cell_f.alignment = left_alignment
            cell_f.border = border

            # Column G: Account Name (Payee)
            cell_g = ws.cell(row=row, column=7)
            cell_g.value = account_name
            cell_g.font = data_font
            cell_g.alignment = left_alignment
            cell_g.border = border

            # Column H: Account Number (Payee)
            cell_h = ws.cell(row=row, column=8)
            cell_h.value = account_number
            cell_h.font = data_font
            cell_h.alignment = left_alignment
            cell_h.border = border

            # Column I: Remark (blank for manual entry)
            cell_i = ws.cell(row=row, column=9)
            cell_i.value = ''
            cell_i.font = data_font
            cell_i.alignment = left_alignment
            cell_i.border = border

            row += 1

        # Add final subtotal for last bank group
        if current_bank is not None and bank_subtotal > 0:
            subtotal_cell = ws.cell(row=row, column=4)
            subtotal_cell.value = f"Subtotal - {current_bank}:"
            subtotal_cell.font = Font(name='Calibri', size=11, bold=True)
            subtotal_cell.alignment = right_alignment
            subtotal_cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
            subtotal_cell.border = border

            subtotal_amount_cell = ws.cell(row=row, column=5)
            subtotal_amount_cell.value = float(bank_subtotal)
            subtotal_amount_cell.font = Font(name='Calibri', size=11, bold=True)
            subtotal_amount_cell.alignment = right_alignment
            subtotal_amount_cell.number_format = '#,##0.00'
            subtotal_amount_cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')
            subtotal_amount_cell.border = border

            # Apply borders to other cells in subtotal row
            for col in [1, 2, 3, 6, 7, 8, 9]:
                cell = ws.cell(row=row, column=col)
                cell.border = border
                cell.fill = PatternFill(start_color='E8F4F8', end_color='E8F4F8', fill_type='solid')

            row += 1

        # ===========================================================================
        # GRAND TOTAL ROW
        # ===========================================================================
        # Column D: "Grand Total:" label
        total_label_cell = ws.cell(row=row, column=4)
        total_label_cell.value = "GRAND TOTAL:"
        total_label_cell.font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
        total_label_cell.alignment = right_alignment
        total_label_cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        total_label_cell.border = border

        # Column E: Total amount
        total_amount_cell = ws.cell(row=row, column=5)
        total_amount_cell.value = float(total_amount)
        total_amount_cell.font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
        total_amount_cell.alignment = right_alignment
        total_amount_cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        total_amount_cell.border = border
        total_amount_cell.number_format = '#,##0.00'

        # Apply borders and fill to other cells in total row
        for col in [1, 2, 3, 6, 7, 8, 9]:
            cell = ws.cell(row=row, column=col)
            cell.border = border
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')

        row += 1

        # ===========================================================================
        # SIGNATURE SECTION (3 ROWS AFTER TOTAL)
        # ===========================================================================
        row += 3  # Add some spacing

        # Merge B:C for "Prepared by"
        ws.merge_cells(f'B{row}:C{row}')
        prepared_cell = ws.cell(row=row, column=2)
        prepared_cell.value = "Prepared by"
        prepared_cell.font = header_font
        prepared_cell.alignment = center_alignment

        # Configure page setup for A4 Landscape
        ws.page_setup.paperSize = 9  # A4 paper size
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToHeight = 0  # Fit all rows on pages as needed
        ws.page_setup.fitToWidth = 1   # Fit to 1 page wide
        ws.print_options.horizontalCentered = True
        ws.print_options.verticalCentered = False

        # Set print area to include all data and signature section
        ws.print_area = f'A1:I{row}'

        # Set margins (in inches) - smaller margins for more space
        ws.page_margins.left = 0.4
        ws.page_margins.right = 0.4
        ws.page_margins.top = 0.5
        ws.page_margins.bottom = 0.5
        ws.page_margins.header = 0.2
        ws.page_margins.footer = 0.2

        # Set zoom/scale for better fit
        ws.page_setup.scale = 100  # 100% scale

        # Enable gridlines for printing
        ws.print_options.gridLines = False
        ws.print_options.gridLinesSet = True

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return output

    def export_to_pdf(self):
        """Export filtered data to PDF with professional formatting"""
        if self.vouchers is None or self.forms is None:
            self.apply_filters()

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)

        # Container for elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=12,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=10,
            spaceBefore=10
        )

        # Title
        title = Paragraph("Payment Vouchers & Forms Report", title_style)
        elements.append(title)

        # Report info
        info_text = f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        info = Paragraph(info_text, styles['Normal'])
        elements.append(info)
        elements.append(Spacer(1, 12))

        # Filter info
        if self.filters.get('date_from') or self.filters.get('date_to') or self.filters.get('status'):
            filter_parts = []
            if self.filters.get('date_from'):
                filter_parts.append(f"From: {self.filters['date_from']}")
            if self.filters.get('date_to'):
                filter_parts.append(f"To: {self.filters['date_to']}")
            if self.filters.get('status') and self.filters['status'] != 'ALL':
                filter_parts.append(f"Status: {self.filters['status']}")

            filter_text = "Filters: " + " | ".join(filter_parts)
            filters_para = Paragraph(filter_text, styles['Normal'])
            elements.append(filters_para)
            elements.append(Spacer(1, 12))

        # Table data
        data = [['No', 'Type', 'Supplier', 'Description', 'Amount', 'Transfer by Account', 'Remark']]

        # Add vouchers
        for voucher in self.vouchers:
            totals = voucher.calculate_grand_total()
            descriptions = " | ".join([item.description for item in voucher.line_items.all()[:2]])[:60]

            # Format amount with currency
            amount_parts = []
            for currency in ['USD', 'KHR', 'THB']:
                if totals.get(currency, 0) > 0:
                    symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}
                    amount_parts.append(f"{symbols[currency]}{totals[currency]:,.2f}")
            amount_display = " + ".join(amount_parts) if amount_parts else "$0.00"

            # Get transfer account info - prioritize company_bank_account
            if voucher.company_bank_account:
                transfer_account = voucher.company_bank_account.get_display_name()[:50]
            elif voucher.bank_name or voucher.bank_account_number:
                # Fallback to manual entry
                parts = []
                if voucher.bank_name:
                    parts.append(voucher.bank_name)
                if voucher.bank_account_number:
                    parts.append(f"Acc '{voucher.bank_account_number}")
                if voucher.bank_address:
                    parts.append(voucher.bank_address)
                transfer_account = ", ".join(parts)[:50]
            else:
                transfer_account = ''

            data.append([
                voucher.pv_number or 'DRAFT',
                'PV',
                voucher.payee_name[:25],
                descriptions,
                amount_display[:20],
                transfer_account,
                ''  # Blank remark
            ])

        # Add forms
        for form in self.forms:
            totals = form.calculate_grand_total()
            descriptions = " | ".join([item.description for item in form.line_items.all()[:2]])[:60]

            # Format amount with currency
            amount_parts = []
            for currency in ['USD', 'KHR', 'THB']:
                if totals.get(currency, 0) > 0:
                    symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}
                    amount_parts.append(f"{symbols[currency]}{totals[currency]:,.2f}")
            amount_display = " + ".join(amount_parts) if amount_parts else "$0.00"

            # Get transfer account info - prioritize company_bank_account
            if form.company_bank_account:
                transfer_account = form.company_bank_account.get_display_name()[:50]
            elif form.bank_name or form.bank_account_number:
                # Fallback to manual entry
                parts = []
                if form.bank_name:
                    parts.append(form.bank_name)
                if form.bank_account_number:
                    parts.append(f"Acc '{form.bank_account_number}")
                if form.bank_address:
                    parts.append(form.bank_address)
                transfer_account = ", ".join(parts)[:50]
            else:
                transfer_account = ''

            data.append([
                form.pf_number or 'DRAFT',
                'PF',
                form.payee_name[:25],
                descriptions,
                amount_display[:20],
                transfer_account,
                ''  # Blank remark
            ])

        # Create table with adjusted column widths for landscape A4
        table = Table(data, colWidths=[0.9*inch, 0.4*inch, 1.3*inch, 2.3*inch, 1.1*inch, 2.5*inch, 1.5*inch])

        # Table style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 24))

        # Summary section
        elements.append(Paragraph("Summary Statistics", heading_style))
        elements.append(Spacer(1, 12))

        stats = self.get_summary_stats()

        summary_data = [
            ['Total Documents:', str(stats['total_documents'])],
            ['Payment Vouchers (PV):', str(stats['total_vouchers'])],
            ['Payment Forms (PF):', str(stats['total_forms'])],
            ['', ''],
            ['Total Amount (USD):', f"${stats['by_currency']['USD']:,.2f}"],
            ['Total Amount (KHR):', f"៛{stats['by_currency']['KHR']:,.2f}"],
            ['Total Amount (THB):', f"฿{stats['by_currency']['THB']:,.2f}"],
        ]

        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, 2), 1, colors.grey),
            ('GRID', (0, 4), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ]))

        elements.append(summary_table)

        # Build PDF
        doc.build(elements)

        buffer.seek(0)
        return buffer
