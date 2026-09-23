"""
Custom User model with enterprise role-based authorization.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone
from apps.core.permissions import UserRole


class CustomUserManager(UserManager):
    """Custom manager ensuring email and role integrity."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Enterprise Custom User for Daizzy IMS.
    Replaces standard Django User with explicit business roles.
    """
    email = models.EmailField('email address', unique=True, db_index=True)
    role = models.CharField(
        max_length=30,
        choices=UserRole.CHOICES,
        default=UserRole.CASHIER,
        db_index=True,
        help_text="Designated authorization role for the user"
    )
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_admin(self):
        return self.role in UserRole.ADMIN_TIER or self.is_superuser

    @property
    def is_manager(self):
        return self.role in UserRole.MANAGER_TIER or self.is_superuser

    @property
    def is_inventory_manager(self):
        return self.role in UserRole.INVENTORY_TIER or self.is_superuser

    @property
    def is_cashier(self):
        return self.role in UserRole.CASHIER_TIER or self.is_superuser
