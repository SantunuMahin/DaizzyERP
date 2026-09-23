"""
Service layer for sales and inventory aggregations.
"""
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from apps.sales.models import Sale, SaleItem
from apps.inventory.models import Inventory
from apps.products.models import Product


class ReportService:
    """Aggregates operational reporting data."""

    @staticmethod
    def get_sales_overview(days: int = 30):
        start_date = timezone.now().date() - timedelta(days=days)
        sales_qs = Sale.objects.filter(created_at__date__gte=start_date, status='COMPLETED')

        total_revenue = sales_qs.aggregate(total=Sum('grand_total'))['total'] or 0.0
        total_orders = sales_qs.count()
        avg_order = (total_revenue / total_orders) if total_orders > 0 else 0.0

        # Breakdown by payment method
        payments_qs = Sale.objects.filter(
            created_at__date__gte=start_date,
            status='COMPLETED'
        ).values('payment__payment_method').annotate(
            total=Sum('grand_total'),
            count=Count('id')
        )

        return {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'avg_order': avg_order,
            'payment_breakdown': list(payments_qs),
        }

    @staticmethod
    def get_top_products(limit: int = 10):
        return SaleItem.objects.filter(
            sale__status='COMPLETED'
        ).values(
            'product__name', 'product__sku', 'product__barcode'
        ).annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('line_total')
        ).order_by('-total_qty')[:limit]

    @staticmethod
    def get_inventory_valuation():
        products = Product.objects.filter(is_active=True).select_related('inventory')
        total_value = sum(p.cost_price * p.current_stock for p in products)
        total_items = sum(p.current_stock for p in products)
        return {
            'total_stock_value': total_value,
            'total_units': total_items,
        }
