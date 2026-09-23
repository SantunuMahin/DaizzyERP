from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity', 'entity_id', 'user', 'ip_address', 'created_at')
    list_filter = ('action', 'entity', 'created_at')
    search_fields = ('action', 'entity', 'user__username')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
