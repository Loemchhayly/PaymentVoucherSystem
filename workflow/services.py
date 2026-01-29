from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


class NotificationService:
    """Service for sending email notifications on workflow events"""

    @staticmethod
    def send_notification(voucher, action, actor, comments=''):
        """
        Send email notification based on workflow action.

        Args:
            voucher: PaymentVoucher instance
            action: str - 'submit', 'approve', 'reject', 'return'
            actor: User who performed the action
            comments: Optional comments
        """
        if action == 'submit':
            NotificationService._notify_next_approver(voucher, actor)
        elif action == 'approve':
            if voucher.status in ['PENDING_L2', 'PENDING_L3', 'PENDING_L4', 'PENDING_L5']:
                # Still pending - notify next approver
                NotificationService._notify_next_approver(voucher, actor)
            elif voucher.status == 'APPROVED':
                # Final approval - notify creator
                NotificationService._notify_creator_approved(voucher, actor)
        elif action == 'reject':
            NotificationService._notify_creator_rejected(voucher, actor, comments)
        elif action == 'return':
            NotificationService._notify_creator_returned(voucher, actor, comments)

    @staticmethod
    def _notify_next_approver(voucher, previous_actor):
        """Notify the next approver in the chain"""
        if not voucher.current_approver:
            return

        subject = f"Payment Voucher {voucher.pv_number} - Pending Your Approval"

        context = {
            'voucher': voucher,
            'approver': voucher.current_approver,
            'previous_actor': previous_actor,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
        }

        html_message = render_to_string('workflow/emails/pending_approval.html', context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[voucher.current_approver.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending approval notification: {e}")

    @staticmethod
    def _notify_creator_approved(voucher, approver):
        """Notify creator that voucher was approved"""
        subject = f"Payment Voucher {voucher.pv_number} - APPROVED"

        context = {
            'voucher': voucher,
            'creator': voucher.created_by,
            'approver': approver,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
        }

        html_message = render_to_string('workflow/emails/voucher_approved.html', context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[voucher.created_by.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending approval notification: {e}")

    @staticmethod
    def _notify_creator_rejected(voucher, rejector, comments):
        """Notify creator that voucher was rejected"""
        subject = f"Payment Voucher {voucher.pv_number} - REJECTED"

        context = {
            'voucher': voucher,
            'creator': voucher.created_by,
            'rejector': rejector,
            'comments': comments,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
        }

        html_message = render_to_string('workflow/emails/voucher_rejected.html', context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[voucher.created_by.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending rejection notification: {e}")

    @staticmethod
    def _notify_creator_returned(voucher, returner, comments):
        """Notify creator that voucher was returned for revision"""
        subject = f"Payment Voucher {voucher.pv_number} - Returned for Revision"

        context = {
            'voucher': voucher,
            'creator': voucher.created_by,
            'returner': returner,
            'comments': comments,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
        }

        html_message = render_to_string('workflow/emails/voucher_returned.html', context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[voucher.created_by.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending return notification: {e}")
