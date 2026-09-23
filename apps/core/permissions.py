"""
Role-based access control (RBAC) permissions for views and DRF APIs.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class UserRole:
    SUPER_ADMIN = 'SUPER_ADMIN'
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    INVENTORY_MANAGER = 'INVENTORY_MANAGER'
    CASHIER = 'CASHIER'
    STAFF = 'STAFF'

    CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (ADMIN, 'Administrator'),
        (MANAGER, 'Branch/Store Manager'),
        (INVENTORY_MANAGER, 'Inventory Manager'),
        (CASHIER, 'Cashier / POS Operator'),
        (STAFF, 'General Staff'),
    ]

    # Hierarchical role tiers for permission inheritance
    ADMIN_TIER = {SUPER_ADMIN, ADMIN}
    MANAGER_TIER = {SUPER_ADMIN, ADMIN, MANAGER}
    INVENTORY_TIER = {SUPER_ADMIN, ADMIN, MANAGER, INVENTORY_MANAGER}
    CASHIER_TIER = {SUPER_ADMIN, ADMIN, MANAGER, CASHIER}
    ALL_ROLES = {SUPER_ADMIN, ADMIN, MANAGER, INVENTORY_MANAGER, CASHIER, STAFF}


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role == UserRole.SUPER_ADMIN or request.user.is_superuser
        ))


class IsAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.ADMIN_TIER or request.user.is_superuser
        ))


class IsManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.MANAGER_TIER or request.user.is_superuser
        ))


class IsInventoryManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.INVENTORY_TIER or request.user.is_superuser
        ))


class IsCashierOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.CASHIER_TIER or request.user.is_superuser
        ))


class IsStaffOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.ALL_ROLES or request.user.is_superuser
        ))


class IsReadOnlyOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (
            request.user.role in UserRole.ADMIN_TIER or request.user.is_superuser
        ))
