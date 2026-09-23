"""
Reporting views.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .services import ReportService


class SalesReportView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = 'reports/sales_report.html'
    allowed_roles = UserRole.MANAGER_TIER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        days = int(self.request.GET.get('days', 30))
        ctx['overview'] = ReportService.get_sales_overview(days=days)
        ctx['top_products'] = ReportService.get_top_products(limit=10)
        ctx['selected_days'] = days
        return ctx


class InventoryReportView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = 'reports/inventory_report.html'
    allowed_roles = UserRole.INVENTORY_TIER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['valuation'] = ReportService.get_inventory_valuation()
        from apps.inventory.services import InventoryService
        ctx['low_stock_products'] = InventoryService.get_low_stock_products()
        return ctx
