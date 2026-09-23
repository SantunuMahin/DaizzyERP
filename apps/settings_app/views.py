"""
Settings management views.
"""
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .models import StoreSettings


class StoreSettingsUpdateView(RoleRequiredMixin, UpdateView):
    model = StoreSettings
    fields = [
        'store_name', 'store_address', 'phone', 'email', 'website', 'logo',
        'currency', 'currency_symbol', 'invoice_prefix', 'invoice_number_format',
        'barcode_format', 'default_tax_rate', 'default_discount_rate',
        'allow_negative_stock', 'low_stock_threshold', 'receipt_width_mm'
    ]
    template_name = 'settings/store_settings.html'
    success_url = reverse_lazy('settings_app:index')
    allowed_roles = UserRole.ADMIN_TIER

    def get_object(self, queryset=None):
        return StoreSettings.get_settings()

    def form_valid(self, form):
        messages.success(self.request, "Store configuration updated successfully.")
        return super().form_valid(form)
