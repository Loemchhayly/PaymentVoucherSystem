from django import forms
from django.forms import inlineformset_factory
from .models import PaymentVoucher, VoucherLineItem, VoucherAttachment, Department, PaymentForm, FormLineItem, FormAttachment, CAMBODIAN_BANKS
from decimal import Decimal


# Custom widget for multiple file uploads
class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget that allows multiple file uploads"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field that handles multiple files"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PaymentVoucherForm(forms.ModelForm):
    """Form for creating/editing payment vouchers"""

    class Meta:
        model = PaymentVoucher
        fields = [
            'pv_number',
            'payee_name',
            'payment_date',
            'company_bank_account',
            'bank_address',
            'bank_name',
            'bank_account_number',
            'status',
        ]
        widgets = {
            'pv_number': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-generated on save'
            }),
            'payee_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payee name'
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'company_bank_account': forms.Select(attrs={
                'class': 'form-control'
            }),
            'bank_address': forms.Select(attrs={
                'class': 'form-control'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name'
            }),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'pv_number': 'PV Number',
            'payee_name': 'Payee Name',
            'payment_date': 'Payment Date',
            'company_bank_account': 'Transfer by Account (Select Company Account)',
            'bank_address': 'Bank (Manual Entry)',
            'bank_name': 'Account Holder Name (Manual Entry)',
            'bank_account_number': 'Account Number (Manual Entry)',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make pv_number not required (it's auto-generated)
        self.fields['pv_number'].required = False

        # Filter company bank accounts to show only active ones
        from .models import CompanyBankAccount
        self.fields['company_bank_account'].queryset = CompanyBankAccount.objects.filter(is_active=True)
        self.fields['company_bank_account'].required = False

        # For new vouchers, make status hidden and set to DRAFT
        if not self.instance.pk:
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = 'DRAFT'

        # Disable fields if voucher is locked
        if self.instance and self.instance.is_locked():
            for field in self.fields:
                self.fields[field].disabled = True


class VoucherLineItemForm(forms.ModelForm):
    """Form for individual line items"""

    class Meta:
        model = VoucherLineItem
        fields = ['line_number', 'description', 'department', 'program', 'amount', 'currency', 'vat_applicable']
        widgets = {
            'line_number': forms.HiddenInput(),
            'description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Description'}),
            'department': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'program': forms.TextInput(
                attrs={'class': 'form-control form-control-sm', 'placeholder': 'Program (optional)'}),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'currency': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'vat_applicable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make line_number not required since view will auto-generate it
        self.fields['line_number'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            if amount <= 0:
                raise forms.ValidationError("Amount must be greater than zero")
            if amount > Decimal('999999999.99'):
                raise forms.ValidationError("Amount is too large")
        return amount


# Formset for dynamic line items
VoucherLineItemFormSet = inlineformset_factory(
    PaymentVoucher,
    VoucherLineItem,
    form=VoucherLineItemForm,
    extra=2,  # Start with 2 empty forms (user can add more dynamically)
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=50  # Maximum 50 line items
)


class VoucherAttachmentForm(forms.Form):
    """Form for uploading multiple attachments"""

    files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png'
        }),
        required=True,
        label='Select Files',
        help_text='Select one or more files to upload (Max 10MB per file)'
    )

    def clean_files(self):
        """Validate uploaded files"""
        files = self.cleaned_data.get('files', [])

        # Handle both single file and list of files
        if not isinstance(files, list):
            files = [files] if files else []

        if not files:
            raise forms.ValidationError('Please select at least one file')

        # File size limit
        max_size = 10 * 1024 * 1024  # 10MB

        # Allowed extensions
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx', '.xls', '.xlsx']

        for file in files:
            # Check file size
            if file.size > max_size:
                raise forms.ValidationError(f'{file.name} exceeds 10MB limit')

            # Check file type
            file_ext = '.' + file.name.split('.')[-1].lower() if '.' in file.name else ''
            if file_ext not in allowed_extensions:
                raise forms.ValidationError(
                    f'{file.name} has invalid file type. '
                    f'Allowed: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG'
                )

        return files


class ApprovalActionForm(forms.Form):
    """Form for approval actions (approve, reject, return)"""

    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('return', 'Return for Revision'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Action"
    )

    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Enter comments (optional for approval, required for reject/return)'}),
        required=False,
        label="Comments"
    )

    requires_md_approval = forms.BooleanField(
        required=False,
        label="Requires MD Approval",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check if this voucher requires Managing Director approval"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.voucher = kwargs.pop('voucher', None)
        super().__init__(*args, **kwargs)

        # Only show MD checkbox for GM (level 4)
        if not self.user or self.user.role_level != 4:
            del self.fields['requires_md_approval']

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        comments = cleaned_data.get('comments', '').strip()

        # Comments required for reject and return
        if action in ['reject', 'return'] and not comments:
            raise forms.ValidationError(f"Comments are required when you {action} a voucher")

        return cleaned_data


# ============================================================================
# PAYMENT FORM FORMS (PF)
# ============================================================================

class PaymentFormForm(forms.ModelForm):
    """Form for creating/editing payment forms"""

    class Meta:
        model = PaymentForm
        fields = [
            'pf_number',
            'payee_name',
            'payment_date',
            'company_bank_account',
            'bank_address',
            'bank_name',
            'bank_account_number',
            'status',
        ]
        widgets = {
            'pf_number': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-generated on save'
            }),
            'payee_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payee name'
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'company_bank_account': forms.Select(attrs={
                'class': 'form-control'
            }),
            'bank_address': forms.Select(attrs={
                'class': 'form-control'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name'
            }),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'pf_number': 'PF Number',
            'payee_name': 'Payee Name',
            'payment_date': 'Payment Date',
            'company_bank_account': 'Transfer by Account (Select Company Account)',
            'bank_address': 'Bank (Manual Entry)',
            'bank_name': 'Account Holder Name (Manual Entry)',
            'bank_account_number': 'Account Number (Manual Entry)',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make pf_number not required (it's auto-generated)
        self.fields['pf_number'].required = False

        # Filter company bank accounts to show only active ones
        from .models import CompanyBankAccount
        self.fields['company_bank_account'].queryset = CompanyBankAccount.objects.filter(is_active=True)
        self.fields['company_bank_account'].required = False

        # For new forms, make status hidden and set to DRAFT
        if not self.instance.pk:
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = 'DRAFT'

        # Disable fields if form is locked
        if self.instance and self.instance.is_locked():
            for field in self.fields:
                self.fields[field].disabled = True


class FormLineItemForm(forms.ModelForm):
    """Form for individual line items in payment form"""

    class Meta:
        model = FormLineItem
        fields = ['line_number', 'description', 'department', 'program', 'amount', 'currency', 'vat_applicable']
        widgets = {
            'line_number': forms.HiddenInput(),
            'description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Description'}),
            'department': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'program': forms.TextInput(
                attrs={'class': 'form-control form-control-sm', 'placeholder': 'Program (optional)'}),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'currency': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'vat_applicable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make line_number not required since view will auto-generate it
        self.fields['line_number'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            if amount <= 0:
                raise forms.ValidationError("Amount must be greater than zero")
            if amount > Decimal('999999999.99'):
                raise forms.ValidationError("Amount is too large")
        return amount


# Formset for dynamic line items in payment form
FormLineItemFormSet = inlineformset_factory(
    PaymentForm,
    FormLineItem,
    form=FormLineItemForm,
    extra=2,  # Start with 2 empty forms
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=50  # Maximum 50 line items
)


class FormAttachmentForm(forms.Form):
    """Form for uploading multiple attachments to payment form"""

    files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png'
        }),
        required=True,
        label='Select Files',
        help_text='Select one or more files to upload (Max 10MB per file)'
    )

    def clean_files(self):
        """Validate uploaded files"""
        files = self.cleaned_data.get('files', [])

        # Handle both single file and list of files
        if not isinstance(files, list):
            files = [files] if files else []

        if not files:
            raise forms.ValidationError('Please select at least one file')

        # File size limit
        max_size = 10 * 1024 * 1024  # 10MB

        # Allowed extensions
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx', '.xls', '.xlsx']

        for file in files:
            # Check file size
            if file.size > max_size:
                raise forms.ValidationError(f'{file.name} exceeds 10MB limit')

            # Check file type
            file_ext = '.' + file.name.split('.')[-1].lower() if '.' in file.name else ''
            if file_ext not in allowed_extensions:
                raise forms.ValidationError(
                    f'{file.name} has invalid file type. '
                    f'Allowed: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG'
                )

        return files