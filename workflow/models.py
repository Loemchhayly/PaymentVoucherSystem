from django.db import models
from django.conf import settings
from vouchers.models import PaymentVoucher, PaymentForm


class ApprovalHistory(models.Model):
    """Track all approval actions on vouchers - immutable audit trail"""

    ACTION_CHOICES = [
        ('SUBMIT', 'Submitted'),
        ('APPROVE', 'Approved'),
        ('REJECT', 'Rejected'),
        ('RETURN', 'Returned for Revision'),
    ]

    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.CASCADE,
        related_name='approval_history'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    actor_role_level = models.IntegerField(
        help_text="Role level of actor at time of action"
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)

    # Signature image (copied from user at time of approval)
    signature_image = models.ImageField(
        upload_to='approval_signatures/%Y/%m/',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name_plural = 'Approval histories'
        indexes = [
            models.Index(fields=['voucher', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor.get_full_name() or self.actor.username} at {self.timestamp}"

    def get_action_badge_class(self):
        """Return Bootstrap badge class for action"""
        action_classes = {
            'SUBMIT': 'primary',
            'APPROVE': 'success',
            'REJECT': 'danger',
            'RETURN': 'warning',
        }
        return action_classes.get(self.action, 'secondary')


class VoucherComment(models.Model):
    """Comments and notes on vouchers"""

    voucher = models.ForeignKey(
        PaymentVoucher,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal notes visible only to approvers"
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.voucher.pv_number or 'DRAFT'}"


# ============================================================================
# PAYMENT FORM WORKFLOW MODELS
# ============================================================================

class FormApprovalHistory(models.Model):
    """Track all approval actions on payment forms - immutable audit trail"""

    ACTION_CHOICES = [
        ('SUBMIT', 'Submitted'),
        ('APPROVE', 'Approved'),
        ('REJECT', 'Rejected'),
        ('RETURN', 'Returned for Revision'),
    ]

    payment_form = models.ForeignKey(
        PaymentForm,
        on_delete=models.CASCADE,
        related_name='approval_history'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    actor_role_level = models.IntegerField(
        help_text="Role level of actor at time of action"
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)

    # Signature image (copied from user at time of approval)
    signature_image = models.ImageField(
        upload_to='approval_signatures/%Y/%m/',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name_plural = 'Form approval histories'
        indexes = [
            models.Index(fields=['payment_form', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor.get_full_name() or self.actor.username} at {self.timestamp}"

    def get_action_badge_class(self):
        """Return Bootstrap badge class for action"""
        action_classes = {
            'SUBMIT': 'primary',
            'APPROVE': 'success',
            'REJECT': 'danger',
            'RETURN': 'warning',
        }
        return action_classes.get(self.action, 'secondary')


class FormComment(models.Model):
    """Comments and notes on payment forms"""

    payment_form = models.ForeignKey(
        PaymentForm,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal notes visible only to approvers"
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.payment_form.pf_number or 'DRAFT'}"
