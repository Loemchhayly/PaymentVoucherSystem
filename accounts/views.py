from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView, FormView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from .forms import UserRegistrationForm, UserLoginForm, SignatureUploadForm, ProfileUpdateForm, PasswordResetRequestForm, PasswordResetConfirmForm
from .utils import send_verification_email, send_welcome_email, send_password_reset_email
from .tokens import verify_token, generate_token
import threading


class RegisterView(CreateView):
    """User registration view with email verification and admin approval"""
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        # Save user but don't activate yet
        user = form.save(commit=False)
        user.is_active = False  # Deactivate until email verified
        user.is_approved = False  # Requires admin approval
        user.save()

        # Send verification email
        if send_verification_email(self.request, user):
            messages.success(
                self.request,
                'Registration successful! Please check your email to verify your account. '
                'After email verification, an administrator will review and approve your account.'
            )
        else:
            messages.warning(
                self.request,
                'Account created but email verification failed. Please contact administrator.'
            )

        # Notify admins about new registration (in background thread)
        thread = threading.Thread(target=self.notify_admins_new_registration, args=(user,))
        thread.daemon = True
        thread.start()

        return redirect(self.success_url)

    def notify_admins_new_registration(self, user):
        """Send email notification to all admin users (runs in background)"""
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = [admin.email for admin in admin_users if admin.email]

        if admin_emails:
            subject = f'New User Registration - {user.username}'
            message = f"""
A new user has registered and requires approval:

Name: {user.get_full_name() or 'N/A'}
Username: {user.username}
Email: {user.email}
Registration Date: {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}

Please log in to the admin panel to review and approve this account.
Admin Panel: {settings.SITE_URL}/admin/auth/user/{user.id}/change/

Note: User must verify their email before they can be approved.
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=True,  # Don't crash if email fails in background
                )
            except Exception as e:
                # Log the error but don't fail the registration
                print(f"Failed to send admin notification: {e}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Register'
        return context


def verify_email(request, uidb64, token):
    """Email verification view"""
    user = verify_token(uidb64, token)

    if user is not None:
        if user.email_verified:
            messages.info(request, 'Email already verified. Waiting for admin approval.')
        else:
            user.email_verified = True
            user.is_active = True  # Activate user (but still needs approval to login)
            user.save()

            # Send welcome email
            send_welcome_email(user)

            messages.success(
                request,
                'Email verified successfully! Your account is now pending administrator approval. '
                'You will receive an email once your account has been approved.'
            )
    else:
        messages.error(
            request,
            'Verification link is invalid or has expired.'
        )

    return redirect('accounts:login')


class LoginView(TemplateView):
    """Custom login view - uses EMAIL instead of username"""
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:home')

        # Get remembered email from cookie
        remembered_email = request.COOKIES.get('remembered_email', '')

        return render(request, self.template_name, {
            'title': 'Login',
            'remembered_email': remembered_email
        })

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        context = {
            'title': 'Login',
            'remembered_email': email  # Keep the email in form
        }

        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, self.template_name, context)

        # Try to find user by email
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return render(request, self.template_name, context)

        # Authenticate using username (Django's authenticate requires username)
        user = authenticate(username=username, password=password)

        if user is not None:
            # Check email verification
            if not user.email_verified:
                messages.error(
                    request,
                    'Please verify your email before logging in. Check your inbox for the verification link.'
                )
                return render(request, self.template_name, context)

            # Check admin approval
            if not user.is_approved:
                messages.error(
                    request,
                    'Your account is pending administrator approval. '
                    'You will receive an email once your account has been approved.'
                )
                return render(request, self.template_name, context)

            # Check if role is assigned
            if not user.role_level:
                messages.warning(
                    request,
                    'Your account has been approved but no role has been assigned yet. '
                    'Please contact the administrator.'
                )
                return render(request, self.template_name, context)

            # All checks passed - login user
            login(request, user)

            # Handle "Remember Me" functionality
            remember_me = request.POST.get('remember')
            if remember_me:
                # Remember for 2 weeks (1209600 seconds)
                request.session.set_expiry(1209600)
            else:
                # Expire when browser closes (default)
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')

            # Check for pending vouchers and notify user
            from vouchers.models import PaymentVoucher
            pending_count = PaymentVoucher.objects.filter(current_approver=user).count()
            if pending_count > 0:
                messages.info(
                    request,
                    f'You have {pending_count} payment voucher{"s" if pending_count > 1 else ""} '
                    f'waiting for your approval. Check the notification bell to view them.'
                )

            # Redirect to next or dashboard
            next_url = request.GET.get('next', 'dashboard:home')
            response = redirect(next_url)

            # Save email in cookie if "Remember Me" is checked
            if remember_me:
                # Remember email for 1 year (365 days)
                response.set_cookie('remembered_email', email, max_age=365*24*60*60, httponly=True)
            else:
                # Clear the cookie if "Remember Me" is not checked
                response.delete_cookie('remembered_email')

            return response
        else:
            messages.error(request, 'Invalid email or password.')

        return render(request, self.template_name, context)


class LogoutView(TemplateView):
    """Logout view"""

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    """User profile view"""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Profile'
        context['approval_status'] = {
            'email_verified': self.request.user.email_verified,
            'is_approved': self.request.user.is_approved,
            'role_assigned': self.request.user.role_level is not None,
        }
        return context


class SignatureUploadView(LoginRequiredMixin, UpdateView):
    """Digital signature upload view"""
    model = User
    form_class = SignatureUploadForm
    template_name = 'accounts/signature_upload.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Signature uploaded successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Upload Signature'
        return context


class PasswordResetRequestView(FormView):
    """Password reset request view - user enters their email"""
    template_name = 'accounts/password_reset.html'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('accounts:password_reset_sent')

    def form_valid(self, form):
        email = form.cleaned_data['email']

        try:
            user = User.objects.get(email=email)

            # Send password reset email
            if send_password_reset_email(self.request, user):
                messages.success(self.request, 'Password reset email sent! Check your inbox.')
            else:
                messages.error(self.request, 'Failed to send reset email. Please try again.')

        except User.DoesNotExist:
            # Don't reveal if email exists or not (security)
            messages.success(self.request, 'If that email exists, a password reset link has been sent.')

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reset Password'
        return context


class PasswordResetSentView(TemplateView):
    """Password reset email sent confirmation"""
    template_name = 'accounts/password_reset_sent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reset Email Sent'
        return context


class PasswordResetConfirmView(FormView):
    """Password reset confirmation view - user sets new password"""
    template_name = 'accounts/password_reset_confirm.html'
    form_class = PasswordResetConfirmForm
    success_url = reverse_lazy('accounts:password_reset_complete')

    def dispatch(self, request, *args, **kwargs):
        # Verify token
        uidb64 = kwargs.get('uidb64')
        token = kwargs.get('token')
        user = verify_token(uidb64, token)

        if user is None:
            messages.error(request, 'Invalid or expired reset link.')
            return redirect('accounts:login')

        self.user = user
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Set new password
        password = form.cleaned_data['password1']
        self.user.set_password(password)
        self.user.save()

        messages.success(self.request, 'Password reset successfully! You can now login with your new password.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Set New Password'
        return context


class PasswordResetCompleteView(TemplateView):
    """Password reset complete view"""
    template_name = 'accounts/password_reset_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Password Reset Complete'
        return context