from django.contrib import admin
from .models import (
    CompanyBankAccount,
    Department,
    PaymentVoucher, VoucherLineItem, VoucherAttachment,
    PaymentForm, FormLineItem, FormAttachment,
    SignatureBatch, BatchVoucherItem, BatchFormItem
)


@admin.register(CompanyBankAccount)
class CompanyBankAccountAdmin(admin.ModelAdmin):
    """Admin interface for Company Bank Account model"""
    list_display = ['company_name', 'account_number', 'currency', 'bank', 'is_active', 'created_at']
    list_filter = ['is_active', 'bank', 'currency']
    search_fields = ['company_name', 'account_number', 'bank']
    ordering = ['company_name', 'bank']

    fieldsets = (
        ('Account Information', {
            'fields': ('company_name', 'account_number', 'currency', 'bank')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model"""
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


class VoucherLineItemInline(admin.TabularInline):
    """Inline for line items in voucher admin"""
    model = VoucherLineItem
    extra = 1
    fields = ['line_number', 'description', 'department', 'program', 'amount', 'vat_applicable']


class VoucherAttachmentInline(admin.TabularInline):
    """Inline for attachments in voucher admin"""
    model = VoucherAttachment
    extra = 0
    readonly_fields = ['filename', 'file_size', 'uploaded_at', 'uploaded_by']
    fields = ['file', 'filename', 'file_size', 'uploaded_at', 'uploaded_by']


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(admin.ModelAdmin):
    """Admin interface for PaymentVoucher model"""
    list_display = ['pv_number', 'payee_name', 'payment_date', 'status', 'current_approver', 'created_by', 'created_at']
    list_filter = ['status', 'created_at', 'payment_date']
    search_fields = ['pv_number', 'payee_name', 'bank_name', 'bank_account_number']
    readonly_fields = ['pv_number', 'created_by', 'created_at', 'updated_at', 'submitted_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['reset_to_l2', 'reset_to_l3', 'reset_to_l4', 'reset_to_l5', 'reset_to_draft', 'mark_approved']

    fieldsets = (
        ('Voucher Information', {
            'fields': ('pv_number', 'status', 'created_by', 'current_approver'),
            'description': 'You can manually change status and current_approver here, or use bulk actions below for common operations.'
        }),
        ('Payee Details', {
            'fields': ('payee_name', 'payment_date')
        }),
        ('Transfer Account', {
            'fields': ('company_bank_account',),
            'description': 'Select a company bank account for the transfer (Recommended)'
        }),
        ('Manual Bank Details (Optional)', {
            'fields': ('bank_address', 'bank_name', 'bank_account_number'),
            'classes': ('collapse',),
            'description': 'Manual entry for backward compatibility. Use "Transfer Account" above instead.'
        }),
        ('Approval Settings', {
            'fields': ('requires_md_approval',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [VoucherLineItemInline, VoucherAttachmentInline]

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Reset to L2 (Department Manager)')
    def reset_to_l2(self, request, queryset):
        """Reset documents to PENDING_L2 status"""
        from accounts.models import User
        updated = 0
        for voucher in queryset:
            # Find L2 approver (Department Manager)
            l2_user = User.objects.filter(role_level=2).first()
            if l2_user:
                voucher.status = 'PENDING_L2'
                voucher.current_approver = l2_user
                voucher.save()
                updated += 1
        self.message_user(request, f'{updated} voucher(s) reset to L2 (Department Manager)')

    @admin.action(description='Reset to L3 (Project Manager)')
    def reset_to_l3(self, request, queryset):
        """Reset documents to PENDING_L3 status"""
        from accounts.models import User
        updated = 0
        for voucher in queryset:
            # Find L3 approver (Project Manager)
            l3_user = User.objects.filter(role_level=3).first()
            if l3_user:
                voucher.status = 'PENDING_L3'
                voucher.current_approver = l3_user
                voucher.save()
                updated += 1
        self.message_user(request, f'{updated} voucher(s) reset to L3 (Project Manager)')

    @admin.action(description='Reset to L4 (General Manager)')
    def reset_to_l4(self, request, queryset):
        """Reset documents to PENDING_L4 status"""
        from accounts.models import User
        updated = 0
        for voucher in queryset:
            # Find L4 approver (General Manager)
            l4_user = User.objects.filter(role_level=4).first()
            if l4_user:
                voucher.status = 'PENDING_L4'
                voucher.current_approver = l4_user
                voucher.save()
                updated += 1
        self.message_user(request, f'{updated} voucher(s) reset to L4 (General Manager)')

    @admin.action(description='Reset to L5 (Managing Director)')
    def reset_to_l5(self, request, queryset):
        """Reset documents to PENDING_L5 status"""
        from accounts.models import User
        updated = 0
        for voucher in queryset:
            # Find L5 approver (MD)
            l5_user = User.objects.filter(role_level=5).first()
            if l5_user:
                voucher.status = 'PENDING_L5'
                voucher.current_approver = l5_user
                voucher.save()
                updated += 1
        self.message_user(request, f'{updated} voucher(s) reset to L5 (MD)')

    @admin.action(description='Reset to Draft')
    def reset_to_draft(self, request, queryset):
        """Reset documents to DRAFT status"""
        updated = queryset.update(status='DRAFT', current_approver=None)
        self.message_user(request, f'{updated} voucher(s) reset to DRAFT')

    @admin.action(description='Mark as Approved')
    def mark_approved(self, request, queryset):
        """Mark documents as APPROVED"""
        updated = queryset.update(status='APPROVED', current_approver=None)
        self.message_user(request, f'{updated} voucher(s) marked as APPROVED')


# ============================================================================
# PAYMENT FORM (PF) ADMIN
# ============================================================================

class FormLineItemInline(admin.TabularInline):
    """Inline for line items in payment form admin"""
    model = FormLineItem
    extra = 1
    fields = ['line_number', 'description', 'department', 'program', 'amount', 'vat_applicable']


class FormAttachmentInline(admin.TabularInline):
    """Inline for attachments in payment form admin"""
    model = FormAttachment
    extra = 0
    readonly_fields = ['filename', 'file_size', 'uploaded_at', 'uploaded_by']
    fields = ['file', 'filename', 'file_size', 'uploaded_at', 'uploaded_by']


@admin.register(PaymentForm)
class PaymentFormAdmin(admin.ModelAdmin):
    """Admin interface for PaymentForm model"""
    list_display = ['pf_number', 'payee_name', 'payment_date', 'status', 'current_approver', 'created_by', 'created_at']
    list_filter = ['status', 'created_at', 'payment_date']
    search_fields = ['pf_number', 'payee_name', 'bank_name', 'bank_account_number']
    readonly_fields = ['pf_number', 'created_by', 'created_at', 'updated_at', 'submitted_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['reset_to_l2', 'reset_to_l3', 'reset_to_l4', 'reset_to_l5', 'reset_to_draft', 'mark_approved']

    fieldsets = (
        ('Payment Form Information', {
            'fields': ('pf_number', 'status', 'created_by', 'current_approver'),
            'description': 'You can manually change status and current_approver here, or use bulk actions below for common operations.'
        }),
        ('Payee Details', {
            'fields': ('payee_name', 'payment_date')
        }),
        ('Transfer Account', {
            'fields': ('company_bank_account',),
            'description': 'Select a company bank account for the transfer (Recommended)'
        }),
        ('Manual Bank Details (Optional)', {
            'fields': ('bank_address', 'bank_name', 'bank_account_number'),
            'classes': ('collapse',),
            'description': 'Manual entry for backward compatibility. Use "Transfer Account" above instead.'
        }),
        ('Approval Settings', {
            'fields': ('requires_md_approval',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [FormLineItemInline, FormAttachmentInline]

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Reset to L2 (Department Manager)')
    def reset_to_l2(self, request, queryset):
        """Reset documents to PENDING_L2 status"""
        from accounts.models import User
        updated = 0
        for form in queryset:
            # Find L2 approver (Department Manager)
            l2_user = User.objects.filter(role_level=2).first()
            if l2_user:
                form.status = 'PENDING_L2'
                form.current_approver = l2_user
                form.save()
                updated += 1
        self.message_user(request, f'{updated} payment form(s) reset to L2 (Department Manager)')

    @admin.action(description='Reset to L3 (Project Manager)')
    def reset_to_l3(self, request, queryset):
        """Reset documents to PENDING_L3 status"""
        from accounts.models import User
        updated = 0
        for form in queryset:
            # Find L3 approver (Project Manager)
            l3_user = User.objects.filter(role_level=3).first()
            if l3_user:
                form.status = 'PENDING_L3'
                form.current_approver = l3_user
                form.save()
                updated += 1
        self.message_user(request, f'{updated} payment form(s) reset to L3 (Project Manager)')

    @admin.action(description='Reset to L4 (General Manager)')
    def reset_to_l4(self, request, queryset):
        """Reset documents to PENDING_L4 status"""
        from accounts.models import User
        updated = 0
        for form in queryset:
            # Find L4 approver (General Manager)
            l4_user = User.objects.filter(role_level=4).first()
            if l4_user:
                form.status = 'PENDING_L4'
                form.current_approver = l4_user
                form.save()
                updated += 1
        self.message_user(request, f'{updated} payment form(s) reset to L4 (General Manager)')

    @admin.action(description='Reset to L5 (Managing Director)')
    def reset_to_l5(self, request, queryset):
        """Reset documents to PENDING_L5 status"""
        from accounts.models import User
        updated = 0
        for form in queryset:
            # Find L5 approver (MD)
            l5_user = User.objects.filter(role_level=5).first()
            if l5_user:
                form.status = 'PENDING_L5'
                form.current_approver = l5_user
                form.save()
                updated += 1
        self.message_user(request, f'{updated} payment form(s) reset to L5 (MD)')

    @admin.action(description='Reset to Draft')
    def reset_to_draft(self, request, queryset):
        """Reset documents to DRAFT status"""
        updated = queryset.update(status='DRAFT', current_approver=None)
        self.message_user(request, f'{updated} payment form(s) reset to DRAFT')

    @admin.action(description='Mark as Approved')
    def mark_approved(self, request, queryset):
        """Mark documents as APPROVED"""
        updated = queryset.update(status='APPROVED', current_approver=None)
        self.message_user(request, f'{updated} payment form(s) marked as APPROVED')


# ============================================================================
# SIGNATURE BATCH ADMIN
# ============================================================================

class BatchVoucherItemInline(admin.TabularInline):
    """Inline for vouchers in batch admin"""
    model = BatchVoucherItem
    extra = 0
    readonly_fields = ['voucher', 'added_at']
    fields = ['voucher', 'added_at']
    can_delete = False


class BatchFormItemInline(admin.TabularInline):
    """Inline for payment forms in batch admin"""
    model = BatchFormItem
    extra = 0
    readonly_fields = ['payment_form', 'added_at']
    fields = ['payment_form', 'added_at']
    can_delete = False


@admin.register(SignatureBatch)
class SignatureBatchAdmin(admin.ModelAdmin):
    """Admin interface for Signature Batch model"""
    list_display = ['batch_number', 'status', 'get_document_count', 'created_by', 'created_at', 'signed_by', 'signed_at']
    list_filter = ['status', 'created_at', 'signed_at']
    search_fields = ['batch_number', 'created_by__username', 'signed_by__username']
    readonly_fields = ['batch_number', 'created_by', 'created_at', 'signed_by', 'signed_at', 'signature_ip']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'status', 'created_by', 'created_at')
        }),
        ('Finance Manager Notes', {
            'fields': ('fm_notes',)
        }),
        ('Signature Information', {
            'fields': ('signed_by', 'signed_at', 'signature_ip', 'md_comments'),
            'classes': ('collapse',)
        }),
    )

    inlines = [BatchVoucherItemInline, BatchFormItemInline]

    def has_add_permission(self, request):
        """Disable adding batches from admin - must be created through the app"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only allow deleting pending batches"""
        if obj and obj.status == 'PENDING':
            return True
        return False