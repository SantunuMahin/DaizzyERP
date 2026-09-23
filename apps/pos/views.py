"""
POS Terminal view.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from apps.settings_app.models import StoreSettings
from apps.sales.models import PaymentMethod


class POSTerminalView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    High-speed, keyboard-friendly Point of Sale (POS) interface.
    Optimized for cashier workflows, hardware scanners, and camera barcode decoding.
    """
    template_name = 'pos/terminal.html'
    allowed_roles = UserRole.CASHIER_TIER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['settings'] = StoreSettings.get_settings()
        ctx['payment_methods'] = PaymentMethod.CHOICES
        return ctx
