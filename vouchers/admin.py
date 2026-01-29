from django.contrib import admin
from .models import Department, PaymentVoucher, VoucherLineItem, VoucherAttachment


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
    list_display = ['pv_number', 'payee_name', 'payment_date', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at', 'payment_date']
    search_fields = ['pv_number', 'payee_name', 'bank_name', 'bank_account']
    readonly_fields = ['pv_number', 'created_by', 'created_at', 'updated_at', 'submitted_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Voucher Information', {
            'fields': ('pv_number', 'status', 'created_by', 'current_approver')
        }),
        ('Payee Details', {
            'fields': ('payee_name', 'payment_date', 'bank_name', 'bank_account')
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
