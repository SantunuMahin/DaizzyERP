"""
Purchases Views.
Provides the procurement dashboard, multi-item fast stock purchase creation,
itemized purchase vouchers, and purchase vs selling product margin analysis.
"""
import json
from decimal import Decimal
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, F

from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from apps.products.models import Product
from apps.inventory.models import Inventory
from .models import Purchase, PurchaseItem, PurchasePaymentStatus
from .services import PurchaseService


class PurchaseListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    Central Procurement & Stock Purchases Dashboard.
    Displays live KPI metrics (Total Spend, Today's Purchases, This Month's Purchases)
    along with filterable purchase history.
    """
    model = Purchase
    template_name = 'purchases/list.html'
    context_object_name = 'purchases'
    paginate_by = 25
    allowed_roles = UserRole.INVENTORY_TIER

    def get_queryset(self):
        qs = Purchase.objects.select_related('created_by').prefetch_related('items').all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(purchase_number__icontains=q) | qs.filter(supplier_name__icontains=q) | qs.filter(supplier_invoice__icontains=q)

        period = self.request.GET.get('period')
        today = timezone.now().date()
        if period == 'today':
            qs = qs.filter(purchase_date=today)
        elif period == 'this_month':
            first_day = today.replace(day=1)
            qs = qs.filter(purchase_date__gte=first_day, purchase_date__lte=today)

        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(payment_status=status_filter)

        return qs.order_by('-purchase_date', '-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kpis'] = PurchaseService.get_purchase_kpis()
        ctx['period_filter'] = self.request.GET.get('period', 'all')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class PurchaseCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    High-productivity multi-item Stock Purchase Creation Form.
    Staff can select multiple catalog products, enter received quantities and cost prices,
    and immediately stock in the inventory with automatic ledger tracking.
    """
    template_name = 'purchases/create.html'
    allowed_roles = UserRole.INVENTORY_TIER

    def get(self, request):
        products = Product.objects.filter(is_active=True).select_related('category', 'inventory').order_by('name')
        return render(request, self.template_name, {
            'products': products,
            'today': timezone.now().date().isoformat(),
        })

    def post(self, request):
        supplier_name = request.POST.get('supplier_name', '').strip()
        supplier_phone = request.POST.get('supplier_phone', '').strip()
        supplier_invoice = request.POST.get('supplier_invoice', '').strip()
        purchase_date_raw = request.POST.get('purchase_date')
        paid_amount_raw = request.POST.get('paid_amount', '0.00')
        notes = request.POST.get('notes', '').strip()

        if not supplier_name:
            messages.error(request, "Supplier or Vendor Name is required.")
            return redirect('purchases:create')

        # Parse item rows
        items_payload = []
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost_price[]')
        update_costs = request.POST.getlist('update_product_cost[]')

        for idx in range(len(product_ids)):
            p_id = product_ids[idx]
            if not p_id:
                continue
            try:
                qty = int(quantities[idx])
                cost = Decimal(str(unit_costs[idx]))
                if qty > 0 and cost >= 0:
                    items_payload.append({
                        'product_id': int(p_id),
                        'quantity': qty,
                        'unit_cost_price': cost,
                        'update_product_cost': True,
                    })
            except (ValueError, IndexError):
                continue

        if not items_payload:
            messages.error(request, "Please add at least one product with valid quantity and cost price.")
            return redirect('purchases:create')

        purchase_date = None
        if purchase_date_raw:
            try:
                purchase_date = timezone.datetime.strptime(purchase_date_raw, '%Y-%m-%d').date()
            except ValueError:
                purchase_date = None

        try:
            purchase = PurchaseService.create_purchase(
                supplier_name=supplier_name,
                items=items_payload,
                supplier_phone=supplier_phone,
                supplier_invoice=supplier_invoice,
                purchase_date=purchase_date,
                paid_amount=Decimal(paid_amount_raw or '0.00'),
                notes=notes,
                created_by=request.user,
            )
            messages.success(
                request,
                f"Purchase #{purchase.purchase_number} successfully registered! {len(items_payload)} items added to inventory."
            )
            return redirect('purchases:detail', pk=purchase.pk)
        except Exception as e:
            messages.error(request, f"Failed to record purchase: {str(e)}")
            return redirect('purchases:create')


class PurchaseDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """
    Detailed goods received note / purchase voucher.
    """
    model = Purchase
    template_name = 'purchases/detail.html'
    context_object_name = 'purchase'
    allowed_roles = UserRole.INVENTORY_TIER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('product').all()
        return ctx


class PurchaseProductsAnalysisView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Analytical comparative view of Purchased Products vs Selling Products.
    Exposes Unit Purchase Cost, Unit Selling Price, Gross Profit Margin %,
    Total Units In Stock, Valuation at Cost vs Retail, and Stock Turn Potential.
    """
    template_name = 'purchases/analysis.html'
    allowed_roles = UserRole.INVENTORY_TIER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        products = Product.objects.filter(is_active=True).select_related('category', 'inventory').order_by('name')

        analysis_items = []
        total_valuation_cost = Decimal('0.00')
        total_valuation_retail = Decimal('0.00')

        for p in products:
            cost = p.cost_price or Decimal('0.00')
            selling = p.selling_price or Decimal('0.00')
            stock = p.current_stock
            margin_amt = selling - cost
            margin_pct = (margin_amt / selling * Decimal('100.0')) if selling > 0 else Decimal('0.00')

            stock_val_cost = cost * Decimal(str(max(0, stock)))
            stock_val_retail = selling * Decimal(str(max(0, stock)))

            total_valuation_cost += stock_val_cost
            total_valuation_retail += stock_val_retail

            analysis_items.append({
                'product': p,
                'cost_price': cost,
                'selling_price': selling,
                'margin_amt': margin_amt,
                'margin_pct': margin_pct,
                'stock': stock,
                'stock_val_cost': stock_val_cost,
                'stock_val_retail': stock_val_retail,
            })

        potential_profit = max(Decimal('0.00'), total_valuation_retail - total_valuation_cost)
        overall_margin_pct = (potential_profit / total_valuation_retail * Decimal('100.0')) if total_valuation_retail > 0 else Decimal('0.00')

        ctx['analysis_items'] = analysis_items
        ctx['total_valuation_cost'] = total_valuation_cost
        ctx['total_valuation_retail'] = total_valuation_retail
        ctx['potential_profit'] = potential_profit
        ctx['overall_margin_pct'] = overall_margin_pct
        return ctx
