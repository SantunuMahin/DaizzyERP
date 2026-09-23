"""
Service layer for user and role operations.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.core.permissions import UserRole

User = get_user_model()


class UserService:
    """Encapsulates business operations relating to users and credentials."""

    @staticmethod
    @transaction.atomic
    def create_user(username: str, email: str, password: str, role: str = UserRole.CASHIER,
                    first_name: str = '', last_name: str = '', phone_number: str = '',
                    is_staff: bool = False) -> User:
        """Create and persist a new staff or operator user."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            is_staff=is_staff or (role in UserRole.ADMIN_TIER)
        )
        return user

    @staticmethod
    def update_role(user: User, new_role: str, modified_by: User) -> User:
        """Safely change user role with permission validation."""
        if not modified_by.is_admin:
            raise PermissionError("Only administrators can reassign user roles.")
        
        user.role = new_role
        user.is_staff = (new_role in UserRole.ADMIN_TIER) or user.is_superuser
        user.save(update_fields=['role', 'is_staff', 'updated_at'])
        return user

    @staticmethod
    def deactivate_user(user: User, modified_by: User) -> User:
        """Soft-deactivate user account."""
        if not modified_by.is_admin:
            raise PermissionError("Only administrators can deactivate users.")
        if user == modified_by:
            raise ValueError("You cannot deactivate your own account.")

        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])
        return user
