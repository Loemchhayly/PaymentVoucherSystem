from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import os

# Cambodian Banks Choices
CAMBODIAN_BANKS = [
    ('ABA Bank', 'ABA Bank'),
    ('ACLEDA Bank', 'ACLEDA Bank'),
    ('MAYBANK (CAMBODIA)PLC', 'MAYBANK (CAMBODIA)PLC'),
    ('HONG LEONG BANK', 'HONG LEONG BANK'),
    ('EMIRATES NBD', 'EMIRATES NBD'),
]

# Currency Choices
CURRENCY_CHOICES = [
    ('USD', 'US Dollar ($)'),
    ('KHR', 'Cambodian Riel (៛)'),
    ('THB', 'Thai Baht (฿)'),
]


class Department(models.Model):
    """Department master data for line items"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class PaymentVoucher(models.Model):
    """Main payment voucher document"""

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_L2', 'Pending Account Supervisor'),
        ('PENDING_L3', 'Pending Finance Manager'),
        ('PENDING_L4', 'Pending General Manager'),
        ('PENDING_L5', 'Pending Managing Director'),
        ('ON_REVISION', 'On Revision'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    # Auto-generated fields
    pv_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Auto-generated PV number in format YYMM-NNNN"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='vouchers_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Header information
    payee_name = models.CharField(max_length=200, verbose_name="Payee Name")
    payment_date = models.DateField(verbose_name="Payment Date")

    # Bank details (corrected field names with defaults for migration)
    bank_address = models.CharField(
        max_length=100,
        choices=CAMBODIAN_BANKS,
        verbose_name="Bank Address",
        help_text="The name of the bank (ABA, ACLEDA, etc.)",
        blank=True,
        default=''
    )
    bank_name = models.CharField(
        max_length=200,
        verbose_name="Bank Name",
        help_text="The name on the bank account (account holder's name)",
        blank=True,
        default=''
    )
    bank_account_number = models.CharField(
        max_length=50,
        verbose_name="Bank Account Number",
        help_text="The account number",
        blank=True,
        default=''
    )

    # GM decision
    requires_md_approval = models.BooleanField(
        default=False,
        help_text="Set by GM: whether MD approval is required"
    )

    # Current approver
    current_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vouchers_pending'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pv_number']),
            models.Index(fields=['status', 'current_approver']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.pv_number or 'DRAFT'} - {self.payee_name}"

    def calculate_grand_total(self):
        """Calculate totals grouped by currency"""
        from collections import defaultdict

        totals = defaultdict(Decimal)
        for item in self.line_items.all():
            totals[item.currency] += item.get_total()

        return dict(totals)

    def get_grand_total_display(self):
        """Return formatted grand total string for display"""
        totals = self.calculate_grand_total()
        symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}

        if not totals:
            return "$0.00"

        # Sort by currency code for consistent display
        parts = []
        for currency in sorted(totals.keys()):
            symbol = symbols.get(currency, currency)
            amount = totals[currency]
            parts.append(f"{symbol}{amount:.2f}")

        return " + ".join(parts)

    def is_editable(self):
        """Check if voucher can be edited"""
        return self.status in ['DRAFT', 'ON_REVISION']

    def is_locked(self):
        """Check if voucher is locked (cannot be edited)"""
        return self.status in ['APPROVED', 'REJECTED']

    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'DRAFT': 'secondary',
            'ON_REVISION': 'warning',
            'PENDING_L2': 'info',
            'PENDING_L3': 'info',
            'PENDING_L4': 'info',
            'PENDING_L5': 'info',
            'APPROVED': 'success',
            'REJECTED': 'danger',
        }
        return status_classes.get(self.status, 'secondary')

    def get_attachment_folder(self):
        """Get the folder path where attachments are stored"""
        if self.pv_number:
            return f"voucher_attachments/{self.pv_number}"
        return f"voucher_attachments/DRAFT-{self.id}"


class VoucherLineItem(models.Model):
    """Individual line items in a voucher"""
    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    line_number = models.PositiveIntegerField()

    description = models.TextField()
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )
    program = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Currency for this line item"
    )
    vat_applicable = models.BooleanField(
        default=False,
        help_text="If checked, 10% VAT will be added"
    )

    class Meta:
        ordering = ['line_number']
        unique_together = [['voucher', 'line_number']]

    def __str__(self):
        return f"Line {self.line_number}: {self.description[:50]}"

    def get_total(self):
        """Calculate line total with VAT if applicable"""
        if self.vat_applicable:
            return self.amount * Decimal('1.1')
        return self.amount

    def get_vat_amount(self):
        """Calculate VAT amount"""
        if self.vat_applicable:
            return self.amount * Decimal('0.1')
        return Decimal('0')

    def get_currency_symbol(self):
        """Return currency symbol"""
        symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}
        return symbols.get(self.currency, '$')

    def get_total_with_currency(self):
        """Return formatted total with currency symbol"""
        return f"{self.get_currency_symbol()}{self.get_total():.2f}"


def voucher_attachment_path(instance, filename):
    """
    Generate upload path for voucher attachments using PV number.
    Path format: voucher_attachments/{PV_NUMBER}/filename.ext
    Example: voucher_attachments/2601-0001/invoice.pdf
    """
    pv_number = instance.voucher.pv_number
    if not pv_number:
        pv_number = f"DRAFT-{instance.voucher.id}"
    filename = os.path.basename(filename)
    return os.path.join('voucher_attachments', pv_number, filename)


class VoucherAttachment(models.Model):
    """File attachments for vouchers"""
    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=voucher_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.get_file_size_display()})"

    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_file_extension(self):
        """Return file extension"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''


# ============================================================================
# PAYMENT FORM MODELS (PF)
# ============================================================================

class PaymentForm(models.Model):
    """Payment Form document - separate from Payment Voucher"""

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_L2', 'Pending Account Supervisor'),
        ('PENDING_L3', 'Pending Finance Manager'),
        ('PENDING_L4', 'Pending General Manager'),
        ('PENDING_L5', 'Pending Managing Director'),
        ('ON_REVISION', 'On Revision'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    # Auto-generated fields
    pf_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Auto-generated PF number in format YYMM-PF-NNNN"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='forms_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Header information
    payee_name = models.CharField(max_length=200, verbose_name="Payee Name")
    payment_date = models.DateField(verbose_name="Payment Date")

    # Bank details (corrected field names with defaults for migration)
    bank_address = models.CharField(
        max_length=100,
        choices=CAMBODIAN_BANKS,
        verbose_name="Bank Address",
        help_text="The name of the bank (ABA, ACLEDA, etc.)",
        blank=True,
        default=''
    )
    bank_name = models.CharField(
        max_length=200,
        verbose_name="Bank Name",
        help_text="The name on the bank account (account holder's name)",
        blank=True,
        default=''
    )
    bank_account_number = models.CharField(
        max_length=50,
        verbose_name="Bank Account Number",
        help_text="The account number",
        blank=True,
        default=''
    )

    # GM decision
    requires_md_approval = models.BooleanField(
        default=False,
        help_text="Set by GM: whether MD approval is required"
    )

    # Current approver
    current_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forms_pending'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pf_number']),
            models.Index(fields=['status', 'current_approver']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.pf_number or 'DRAFT'} - {self.payee_name}"

    def calculate_grand_total(self):
        """Calculate totals grouped by currency"""
        from collections import defaultdict

        totals = defaultdict(Decimal)
        for item in self.line_items.all():
            totals[item.currency] += item.get_total()

        return dict(totals)

    def get_grand_total_display(self):
        """Return formatted grand total string for display"""
        totals = self.calculate_grand_total()
        symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}

        if not totals:
            return "$0.00"

        # Sort by currency code for consistent display
        parts = []
        for currency in sorted(totals.keys()):
            symbol = symbols.get(currency, currency)
            amount = totals[currency]
            parts.append(f"{symbol}{amount:.2f}")

        return " + ".join(parts)

    def is_editable(self):
        """Check if form can be edited"""
        return self.status in ['DRAFT', 'ON_REVISION']

    def is_locked(self):
        """Check if form is locked (cannot be edited)"""
        return self.status in ['APPROVED', 'REJECTED']

    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'DRAFT': 'secondary',
            'ON_REVISION': 'warning',
            'PENDING_L2': 'info',
            'PENDING_L3': 'info',
            'PENDING_L4': 'info',
            'PENDING_L5': 'info',
            'APPROVED': 'success',
            'REJECTED': 'danger',
        }
        return status_classes.get(self.status, 'secondary')

    def get_attachment_folder(self):
        """Get the folder path where attachments are stored"""
        if self.pf_number:
            return f"form_attachments/{self.pf_number}"
        return f"form_attachments/DRAFT-{self.id}"


class FormLineItem(models.Model):
    """Individual line items in a payment form"""
    payment_form = models.ForeignKey(
        PaymentForm,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    line_number = models.PositiveIntegerField()

    description = models.TextField()
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )
    program = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Currency for this line item"
    )
    vat_applicable = models.BooleanField(
        default=False,
        help_text="If checked, 10% VAT will be added"
    )

    class Meta:
        ordering = ['line_number']
        unique_together = [['payment_form', 'line_number']]

    def __str__(self):
        return f"Line {self.line_number}: {self.description[:50]}"

    def get_total(self):
        """Calculate line total with VAT if applicable"""
        if self.vat_applicable:
            return self.amount * Decimal('1.1')
        return self.amount

    def get_vat_amount(self):
        """Calculate VAT amount"""
        if self.vat_applicable:
            return self.amount * Decimal('0.1')
        return Decimal('0')

    def get_currency_symbol(self):
        """Return currency symbol"""
        symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}
        return symbols.get(self.currency, '$')

    def get_total_with_currency(self):
        """Return formatted total with currency symbol"""
        return f"{self.get_currency_symbol()}{self.get_total():.2f}"


def form_attachment_path(instance, filename):
    """
    Generate upload path for form attachments using PF number.
    Path format: form_attachments/{PF_NUMBER}/filename.ext
    Example: form_attachments/2601-PF-0001/invoice.pdf
    """
    pf_number = instance.payment_form.pf_number
    if not pf_number:
        pf_number = f"DRAFT-{instance.payment_form.id}"
    filename = os.path.basename(filename)
    return os.path.join('form_attachments', pf_number, filename)


class FormAttachment(models.Model):
    """File attachments for payment forms"""
    payment_form = models.ForeignKey(
        PaymentForm,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=form_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.get_file_size_display()})"

    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_file_extension(self):
        """Return file extension"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''