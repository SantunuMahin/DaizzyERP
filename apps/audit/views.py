"""
Audit log presentation view.
"""
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = AuditLog
    template_name = 'audit/list.html'
    context_object_name = 'audit_logs'
    paginate_by = 35
    allowed_roles = UserRole.ADMIN_TIER

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').all()
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
        entity = self.request.GET.get('entity')
        if entity:
            qs = qs.filter(entity=entity)
        return qs.order_by('-created_at')
