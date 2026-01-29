from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class ApprovedUserBackend(ModelBackend):
    """
    Custom authentication backend that only allows approved users to login
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # First authenticate normally
        user = super().authenticate(request, username=username, password=password, **kwargs)

        if user is None:
            return None

        # Check if user is approved
        if not user.is_approved:
            return None

        return user

    def user_can_authenticate(self, user):
        """
        Reject users that are not approved or whose accounts are inactive.
        """
        is_active = getattr(user, 'is_active', None)
        is_approved = getattr(user, 'is_approved', None)

        return is_active and is_approved