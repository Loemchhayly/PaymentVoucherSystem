from django.contrib import admin
from .models import ApprovalHistory, FormApprovalHistory, VoucherComment


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    """Admin interface for ApprovalHistory (read-only)"""
    list_display = ['voucher', 'action', 'actor', 'actor_role_level', 'timestamp']
    list_filter = ['action', 'actor_role_level', 'timestamp']
    search_fields = ['voucher__pv_number', 'voucher__payee_name', 'actor__username', 'actor__email']
    readonly_fields = ['voucher', 'action', 'actor', 'actor_role_level', 'timestamp', 'comments', 'signature_image']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        # Approval history is created automatically, not manually
        return False

    def has_delete_permission(self, request, obj=None):
        # Immutable audit trail - cannot delete
        return False


@admin.register(FormApprovalHistory)
class FormApprovalHistoryAdmin(admin.ModelAdmin):
    """Admin interface for FormApprovalHistory (read-only)"""
    list_display = ['payment_form', 'action', 'actor', 'actor_role_level', 'timestamp']
    list_filter = ['action', 'actor_role_level', 'timestamp']
    search_fields = ['payment_form__pf_number', 'payment_form__payee_name', 'actor__username', 'actor__email']
    readonly_fields = ['payment_form', 'action', 'actor', 'actor_role_level', 'timestamp', 'comments', 'signature_image']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        # Approval history is created automatically, not manually
        return False

    def has_delete_permission(self, request, obj=None):
        # Immutable audit trail - cannot delete
        return False


@admin.register(VoucherComment)
class VoucherCommentAdmin(admin.ModelAdmin):
    """Admin interface for VoucherComment"""
    list_display = ['voucher', 'user', 'created_at', 'is_internal']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['voucher__pv_number', 'voucher__payee_name', 'user__username', 'comment']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
