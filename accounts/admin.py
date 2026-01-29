from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin with approval functionality
    """

    list_display = [
        'username',
        'email',
        'full_name_display',
        'role_status',
        'approval_status',
        'email_status',
        'is_active',
        'date_joined'
    ]

    list_filter = [
        'is_approved',
        'email_verified',
        'role_level',
        'is_staff',
        'is_active',
        'date_joined'
    ]

    search_fields = [
        'username',
        'email',
        'first_name',
        'last_name'
    ]

    readonly_fields = [
        'date_joined',
        'last_login',
        'approved_at',
        'approved_by'
    ]

    actions = [
        'approve_users',
        'reject_users',
        'send_approval_reminder'
    ]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Role & Signature', {'fields': ('role_level', 'signature_image')}),
        ('Verification & Approval', {
            'fields': ('email_verified', 'is_approved', 'approved_by', 'approved_at'),
            'description': 'Email must be verified before user can be approved.'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )

    def full_name_display(self, obj):
        """Display full name or username"""
        full_name = obj.get_full_name() if hasattr(obj, 'get_full_name') else ''
        if full_name and full_name.strip():
            return full_name
        return '-'

    full_name_display.short_description = 'Full Name'

    def role_status(self, obj):
        """Display role assignment status"""
        if obj.role_level:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.get_role_level_display()
            )
        # FIXED: Added {} placeholder and empty string argument
        return format_html(
            '<span style="color: gray;">⚠ Not Assigned{}</span>',
            ''
        )

    role_status.short_description = 'Role'

    def approval_status(self, obj):
        """Display approval status with color coding"""
        if obj.is_approved:
            approved_date = obj.approved_at.strftime('%Y-%m-%d') if obj.approved_at else 'Unknown'
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span><br><small>{}</small>',
                approved_date
            )
        else:
            if obj.email_verified:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⏳ Pending Approval{}</span>',
                    ''
                )
            else:
                return format_html(
                    '<span style="color: red; font-weight: bold;">✉ Email Not Verified{}</span>',
                    ''
                )

    approval_status.short_description = 'Approval Status'

    def email_status(self, obj):
        """Display email verification status"""
        if obj.email_verified:
            return format_html(
                '<span style="color: green;">✓ Verified{}</span>',
                ''
            )
        return format_html(
            '<span style="color: red;">✗ Not Verified{}</span>',
            ''
        )

    email_status.short_description = 'Email'

    def approve_users(self, request, queryset):
        """Bulk approve selected users"""
        # Filter only users who have verified email but not approved
        pending_users = queryset.filter(is_approved=False, email_verified=True)
        not_verified = queryset.filter(is_approved=False, email_verified=False)

        if not_verified.exists():
            self.message_user(
                request,
                f'{not_verified.count()} user(s) cannot be approved because email is not verified.',
                level='warning'
            )

        count = 0
        for user in pending_users:
            user.is_approved = True
            user.approved_by = request.user
            user.approved_at = timezone.now()
            user.save()

            # Send approval email to user
            self.send_approval_email(user)
            count += 1

        if count > 0:
            self.message_user(
                request,
                f'{count} user(s) have been approved successfully and notified via email.'
            )
        else:
            self.message_user(
                request,
                'No users were approved. Make sure users have verified their email first.',
                level='warning'
            )

    approve_users.short_description = 'Approve selected users (email verified only)'

    def reject_users(self, request, queryset):
        """Bulk reject selected users"""
        pending_users = queryset.filter(is_approved=False)
        count = pending_users.count()

        for user in pending_users:
            # Send rejection email
            self.send_rejection_email(user)
            # Deactivate account
            user.is_active = False
            user.save()

        self.message_user(
            request,
            f'{count} user(s) have been rejected and notified via email.'
        )

    reject_users.short_description = 'Reject selected users'

    def send_approval_reminder(self, request, queryset):
        """Send reminder to users with pending approval"""
        pending_users = queryset.filter(is_approved=False, email_verified=True, is_active=True)
        count = 0

        for user in pending_users:
            if user.email:
                subject = 'Account Status - Garden City Water Park'
                message = f"""
Hello {user.get_full_name() or user.username},

Your account registration is currently under review by our administrators.

Status:
- Email Verification: ✓ Completed
- Admin Approval: ⏳ Pending

We will notify you via email once your account has been reviewed and approved.

If you have any questions, please contact the system administrator.

Best regards,
Garden City Water Park Team
                """

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    count += 1
                except Exception as e:
                    print(f"Failed to send reminder to {user.email}: {e}")

        self.message_user(
            request,
            f'Sent status reminder to {count} user(s).'
        )

    send_approval_reminder.short_description = 'Send approval status reminder'

    def send_approval_email(self, user):
        """Send approval notification email"""
        if user.email:
            subject = 'Account Approved - Garden City Water Park'

            # Check if role is assigned
            role_message = ""
            if user.role_level:
                role_message = f"\nYour assigned role: {user.get_role_level_display()}"
            else:
                role_message = "\n\nNote: Your role has not been assigned yet. An administrator will assign your role shortly."

            message = f"""
Hello {user.get_full_name() or user.username},

Great news! Your account has been approved by the administrator.

You can now log in to the Payment Voucher System:
Login URL: {settings.SITE_URL}/accounts/login/
{role_message}

Welcome to Garden City Water Park Payment Voucher System!

If you have any questions, please contact the system administrator.

Best regards,
Garden City Water Park Team
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send approval email to {user.email}: {e}")

    def send_rejection_email(self, user):
        """Send rejection notification email"""
        if user.email:
            subject = 'Account Registration - Update'
            message = f"""
Hello {user.get_full_name() or user.username},

We regret to inform you that your account registration for the Garden City Water Park 
Payment Voucher System could not be approved at this time.

If you believe this is an error or would like more information, 
please contact the system administrator.

Best regards,
Garden City Water Park Team
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send rejection email to {user.email}: {e}")