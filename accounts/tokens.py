from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for email verification.
    Uses Django's built-in PasswordResetTokenGenerator as base.
    """

    def _make_hash_value(self, user, timestamp):
        """
        Include user's email_verified status in the hash so token becomes invalid
        after email is verified.
        """
        return (
            str(user.pk) + str(timestamp) + str(user.email_verified)
        )


email_verification_token = EmailVerificationTokenGenerator()


def generate_verification_token(user):
    """Generate verification token for user"""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    return uid, token


def verify_token(uidb64, token):
    """
    Verify the token and return user if valid.
    Works for both email verification and password reset tokens.
    Returns None if invalid.
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)

        # Try email verification token first, then password reset token
        if email_verification_token.check_token(user, token):
            return user
        elif password_reset_token.check_token(user, token):
            return user
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass

    return None


# Generic token generator for password reset
password_reset_token = PasswordResetTokenGenerator()


def generate_token(user):
    """Generate token for password reset"""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token.make_token(user)
    return uid, token
