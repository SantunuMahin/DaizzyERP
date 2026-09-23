"""
Dashboard and core system views.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, Count


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main operational executive dashboard for staff and managers.
    Aggregates operational inventory, sales, and low-stock indicators.
    """
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Placeholders with safe lookups before data modules are populated
        total_products = 0
        low_stock_count = 0
        out_of_stock_count = 0
        today_orders = 0
        today_revenue = 0.0
        recent_sales = []
        recent_movements = []

        try:
            from apps.products.models import Product
            total_products = Product.objects.filter(is_active=True).count()
        except Exception:
            pass

        try:
            from apps.inventory.models import Inventory, InventoryTransaction
            low_stock_count = Inventory.objects.filter(
                quantity__gt=0,
                quantity__lte=5
            ).count()
            out_of_stock_count = Inventory.objects.filter(quantity=0).count()
            recent_movements = InventoryTransaction.objects.select_related(
                'product', 'created_by'
            ).order_by('-created_at')[:8]
        except Exception:
            pass

        try:
            from apps.sales.models import Sale
            today_sales_qs = Sale.objects.filter(
                created_at__date=today,
                status='COMPLETED'
            )
            today_orders = today_sales_qs.count()
            today_revenue = today_sales_qs.aggregate(total=Sum('grand_total'))['total'] or 0.0
            recent_sales = Sale.objects.select_related('cashier').order_by('-created_at')[:8]
        except Exception:
            pass

        context.update({
            'page_title': 'Executive Dashboard',
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'today_orders': today_orders,
            'today_revenue': today_revenue,
            'recent_sales': recent_sales,
            'recent_movements': recent_movements,
        })
        return context
