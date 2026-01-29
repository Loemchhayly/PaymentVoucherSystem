from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .tokens import generate_verification_token


def send_verification_email(request, user):
    """
    Send email verification link to user.

    Args:
        request: HTTP request object (for building absolute URL)
        user: User instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Generate token
    uid, token = generate_verification_token(user)

    # Build verification URL
    verification_url = request.build_absolute_uri(
        f'/accounts/verify-email/{uid}/{token}/'
    )

    # Email subject
    subject = 'Verify your email - Payment Voucher System'

    # Render HTML email template
    html_message = render_to_string('accounts/emails/verification_email.html', {
        'user': user,
        'verification_url': verification_url,
        'site_name': 'Payment Voucher System',
    })

    # Plain text version
    plain_message = strip_tags(html_message)

    # Send email
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_welcome_email(user):
    """
    Send welcome email after email verification.

    Args:
        user: User instance
    """
    subject = 'Welcome to Payment Voucher System'

    html_message = render_to_string('accounts/emails/welcome_email.html', {
        'user': user,
        'site_name': 'Payment Voucher System',
    })

    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending welcome email: {e}")


def send_password_reset_email(request, user):
    """
    Send password reset email to user.

    Args:
        request: HTTP request object (for building absolute URL)
        user: User instance

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    from .tokens import generate_token

    # Generate token
    uid, token = generate_token(user)

    # Build reset URL
    reset_url = request.build_absolute_uri(
        f'/accounts/password-reset/{uid}/{token}/'
    )

    # Email subject
    subject = 'Password Reset Request - Payment Voucher System'

    # Render HTML email template
    html_message = render_to_string('accounts/emails/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
        'site_name': 'Payment Voucher System',
    })

    # Plain text version
    plain_message = strip_tags(html_message)

    # Send email
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False
