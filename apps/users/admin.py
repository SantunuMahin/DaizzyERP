"""
Admin integration for User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Business Role & Info', {
            'fields': ('role', 'phone_number')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Business Role & Info', {
            'fields': ('email', 'role', 'phone_number')
        }),
    )
