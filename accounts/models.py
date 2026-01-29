from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with role levels and digital signature support.

    Role Levels:
    1 - Financial Officer (Creator)
    2 - Financial Supervisor (First Reviewer)
    3 - Finance Manager (Second Reviewer)
    4 - General Manager (Third Reviewer)
    5 - Managing Director (Final Optional Reviewer)
    """

    ROLE_CHOICES = [
        (1, 'Financial Officer'),
        (2, 'Financial Supervisor'),
        (3, 'Finance Manager'),
        (4, 'General Manager'),
        (5, 'Managing Director'),
    ]

    role_level = models.IntegerField(
        choices=ROLE_CHOICES,
        null=True,
        blank=True,
        help_text="User's role level in the approval chain"
    )

    signature_image = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True,
        help_text="Digital signature image (PNG format recommended)"
    )

    email_verified = models.BooleanField(
        default=False,
        help_text="Email verification status"
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )

    # Admin approval field
    is_approved = models.BooleanField(
        default=False,
        help_text="Admin approval status for new account"
    )

    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        help_text="Admin who approved this account"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when account was approved"
    )

    class Meta:
        db_table = 'auth_user'
        ordering = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_level_display() or 'No Role'})"

    def get_role_name(self):
        """Return the role name as string"""
        return self.get_role_level_display() if self.role_level else 'No Role Assigned'

    def can_approve_level(self, level):
        """Check if user can approve at given level"""
        return self.role_level == level if self.role_level else False

    def is_account_active(self):
        """Check if account is fully active (approved, verified, and active)"""
        return self.is_active and self.is_approved and self.email_verified