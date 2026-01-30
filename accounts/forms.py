from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class UserRegistrationForm(UserCreationForm):
    """User registration form with email verification"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Check for spaces
        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")

        # Check minimum length
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")

        # Check for invalid characters (only letters, numbers, and underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, and underscores.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class UserLoginForm(AuthenticationForm):
    """Custom login form with Bootstrap styling"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class SignatureUploadForm(forms.ModelForm):
    """Form for uploading digital signature image"""

    class Meta:
        model = User
        fields = ['signature_image']
        widgets = {
            'signature_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png,image/jpeg,image/jpg'})
        }

    def clean_signature_image(self):
        image = self.cleaned_data.get('signature_image')

        if image:
            # Check file size (max 2MB)
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image size should not exceed 2MB")

            # Check file type
            if not image.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError("Only PNG, JPG, and JPEG formats are allowed")

        return image


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+855 12 345 678'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email is readonly (cannot be changed after registration)
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].help_text = "Email cannot be changed after registration"


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset"""

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autocomplete': 'email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            # Don't reveal if email exists (security)
            pass
        return email


class PasswordResetConfirmForm(forms.Form):
    """Form for setting new password"""

    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )

    password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords do not match.")

            # Password strength validation
            if len(password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")

        return cleaned_data
