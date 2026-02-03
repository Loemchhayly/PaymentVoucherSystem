from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import FileResponse, Http404
from pathlib import Path
from .models import ApprovalHistory, FormApprovalHistory, VoucherComment, BackupHistory


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


@admin.register(BackupHistory)
class BackupHistoryAdmin(admin.ModelAdmin):
    """Admin interface for BackupHistory"""
    list_display = [
        'created_at',
        'status_badge',
        'database_type',
        'file_name',
        'file_size_formatted',
        'duration_formatted',
        'download_link'
    ]
    list_filter = ['status', 'database_type', 'created_at']
    search_fields = ['file_name', 'error_message']
    readonly_fields = [
        'created_at',
        'status',
        'database_type',
        'file_name',
        'file_path',
        'file_size',
        'error_message',
        'duration_seconds',
        'file_size_formatted',
        'duration_formatted',
        'download_link'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Backup Information', {
            'fields': ('created_at', 'status', 'database_type')
        }),
        ('File Details', {
            'fields': ('file_name', 'file_path', 'file_size', 'file_size_formatted', 'download_link')
        }),
        ('Performance', {
            'fields': ('duration_seconds', 'duration_formatted')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Backups are created automatically via management command
        return False

    def has_change_permission(self, request, obj=None):
        # Backup history is read-only
        return False

    def status_badge(self, obj):
        """Display status as a colored badge"""
        color_map = {
            'SUCCESS': 'green',
            'FAILED': 'red',
            'IN_PROGRESS': 'orange',
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def file_size_formatted(self, obj):
        """Display file size in human-readable format"""
        return obj.get_file_size_display()
    file_size_formatted.short_description = 'File Size'

    def duration_formatted(self, obj):
        """Display duration in human-readable format"""
        if obj.duration_seconds is None:
            return 'N/A'
        return f'{obj.duration_seconds:.2f}s'
    duration_formatted.short_description = 'Duration'

    def download_link(self, obj):
        """Provide download link for backup file"""
        if obj.file_path and Path(obj.file_path).exists():
            return format_html(
                '<a href="/media/backups/{}" download>Download Backup</a>',
                obj.file_name
            )
        return format_html('<span style="color: red;">File not found</span>')
    download_link.short_description = 'Download'
