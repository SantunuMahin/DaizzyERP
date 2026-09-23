"""
Core mixins for Django views.
"""
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(AccessMixin):
    """
    Verify that the current user is authenticated and possesses
    one of the specified allowed roles.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_role = getattr(request.user, 'role', None)
        if not self.allowed_roles or user_role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "You do not have permission to access that resource.")
        raise PermissionDenied("User does not have sufficient role privileges.")
