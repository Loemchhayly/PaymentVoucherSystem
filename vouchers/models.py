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


class CompanyBankAccount(models.Model):
    """Company bank accounts for transfer"""
    company_name = models.CharField(
        max_length=200,
        verbose_name="Company Name",
        help_text="e.g., Phat Phnom Penh Co.,Ltd"
    )
    account_number = models.CharField(
        max_length=50,
        verbose_name="Account Number",
        help_text="e.g., 002 232 482"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        verbose_name="Currency"
    )
    bank = models.CharField(
        max_length=100,
        choices=CAMBODIAN_BANKS,
        verbose_name="Bank",
        help_text="The bank where this account is held"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive accounts won't be shown in selection"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['company_name', 'bank']
        unique_together = [['account_number', 'bank']]

    def __str__(self):
        return f"{self.company_name}, Account Number '{self.account_number} ({self.currency}) {self.bank}"

    def get_display_name(self):
        """Full display name for forms"""
        return f"{self.company_name}, Account Number '{self.account_number} ({self.currency}) {self.bank}"


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

    # NEW: Company bank account for transfer (preferred method)
    company_bank_account = models.ForeignKey(
        'CompanyBankAccount',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Transfer by Account",
        help_text="Select the company bank account for this transfer"
    )

    # Bank details (corrected field names with defaults for migration)
    # NOTE: These are kept for backward compatibility and manual entry
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
        help_text="Auto-generated PF number in format YYMM-NNNN"
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

    # NEW: Company bank account for transfer (preferred method)
    company_bank_account = models.ForeignKey(
        'CompanyBankAccount',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Transfer by Account",
        help_text="Select the company bank account for this transfer"
    )

    # Bank details (corrected field names with defaults for migration)
    # NOTE: These are kept for backward compatibility and manual entry
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
    Example: form_attachments/2601-0001/invoice.pdf
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

# ============================================================================
# BATCH SIGNATURE SYSTEM
# ============================================================================

class SignatureBatch(models.Model):
    """Batch of vouchers for MD signature"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending MD Signature'),
        ('SIGNED', 'Signed by MD'),
        ('REJECTED', 'Rejected by MD'),
    ]

    # Batch identification
    batch_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated batch number (BATCH-YYYYMMDD-NNN)"
    )

    # Created by Finance Manager
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='signature_batches_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    # MD signature details
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='signature_batches_signed',
        null=True,
        blank=True
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    signature_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address when MD signed"
    )

    # Comments/notes
    fm_notes = models.TextField(
        blank=True,
        verbose_name="Finance Manager Notes"
    )
    md_comments = models.TextField(
        blank=True,
        verbose_name="MD Comments"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Signature Batch"
        verbose_name_plural = "Signature Batches"

    def __str__(self):
        return f"{self.batch_number} - {self.get_status_display()}"

    def generate_batch_number(self):
        """Generate unique batch number: BATCH-YYYYMMDD-NNN"""
        from datetime import date
        today = date.today()
        date_str = today.strftime('%Y%m%d')

        # Count batches created today
        today_count = SignatureBatch.objects.filter(
            batch_number__startswith=f'BATCH-{date_str}'
        ).count()

        # Generate new number
        new_number = f'BATCH-{date_str}-{(today_count + 1):03d}'
        return new_number

    def get_vouchers(self):
        """Get all vouchers in this batch"""
        return self.voucher_items.select_related('voucher').all()

    def get_forms(self):
        """Get all payment forms in this batch"""
        return self.form_items.select_related('payment_form').all()

    def get_total_amount(self):
        """Calculate total amount of all documents in batch"""
        total = {'USD': Decimal('0'), 'KHR': Decimal('0'), 'THB': Decimal('0')}

        # Add voucher totals
        for item in self.voucher_items.all():
            voucher_totals = item.voucher.calculate_grand_total()
            for currency in total.keys():
                total[currency] += voucher_totals.get(currency, Decimal('0'))

        # Add form totals
        for item in self.form_items.all():
            form_totals = item.payment_form.calculate_grand_total()
            for currency in total.keys():
                total[currency] += form_totals.get(currency, Decimal('0'))

        return total

    def get_total_amount_display(self):
        """Return formatted total amount string for display"""
        totals = self.get_total_amount()
        symbols = {'USD': '$', 'KHR': '៛', 'THB': '฿'}

        # Filter out zero amounts
        parts = []
        for currency in sorted(totals.keys()):
            amount = totals[currency]
            if amount > 0:
                symbol = symbols.get(currency, currency)
                parts.append(f"{symbol}{amount:,.2f}")

        return " + ".join(parts) if parts else "$0.00"

    def get_document_count(self):
        """Get total number of documents in batch"""
        return self.voucher_items.count() + self.form_items.count()

    def save(self, *args, **kwargs):
        # Generate batch number if not set
        if not self.batch_number:
            self.batch_number = self.generate_batch_number()
        super().save(*args, **kwargs)


class BatchVoucherItem(models.Model):
    """Payment Voucher in a signature batch"""
    batch = models.ForeignKey(
        SignatureBatch,
        on_delete=models.CASCADE,
        related_name='voucher_items'
    )
    voucher = models.ForeignKey(
        'PaymentVoucher',
        on_delete=models.CASCADE,
        related_name='batch_items'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['batch', 'voucher']]
        ordering = ['added_at']

    def __str__(self):
        return f"{self.batch.batch_number} - {self.voucher.pv_number}"


class BatchFormItem(models.Model):
    """Payment Form in a signature batch"""
    batch = models.ForeignKey(
        SignatureBatch,
        on_delete=models.CASCADE,
        related_name='form_items'
    )
    payment_form = models.ForeignKey(
        'PaymentForm',
        on_delete=models.CASCADE,
        related_name='batch_items'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['batch', 'payment_form']]
        ordering = ['added_at']

    def __str__(self):
        return f"{self.batch.batch_number} - {self.payment_form.pf_number}"
