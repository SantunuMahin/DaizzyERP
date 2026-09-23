"""
Inventory management and stock ledger views.
"""
from django.views.generic import ListView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from apps.products.models import Product
from .models import Inventory, InventoryTransaction, InventoryTransactionType
from .services import StockAdjustmentService


class StockAdjustmentForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'adjust-product-select'})
    )
    transaction_type = forms.ChoiceField(
        choices=[
            (InventoryTransactionType.PURCHASE, 'Stock Addition (Purchase)'),
            (InventoryTransactionType.ADJUSTMENT_IN, 'Manual Addition (+)'),
            (InventoryTransactionType.ADJUSTMENT_OUT, 'Manual Deduction (-)'),
            (InventoryTransactionType.DAMAGE, 'Damaged Stock (-)'),
            (InventoryTransactionType.LOSS, 'Lost / Missing Stock (-)'),
            (InventoryTransactionType.CORRECTION, 'Inventory Count Correction'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Quantity'})
    )
    reason = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Reason for adjustment (required)'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Additional context/notes'})
    )


class StockOverviewView(LoginRequiredMixin, ListView):
    model = Inventory
    template_name = 'inventory/overview.html'
    context_object_name = 'inventories'
    paginate_by = 25

    def get_queryset(self):
        qs = Inventory.objects.select_related('product', 'product__category').filter(product__is_active=True)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(product__name__icontains=search) | qs.filter(product__barcode__icontains=search) | qs.filter(product__sku__icontains=search)
        filter_status = self.request.GET.get('status')
        if filter_status == 'low':
            qs = qs.filter(quantity__gt=0, quantity__lte=5)
        elif filter_status == 'out':
            qs = qs.filter(quantity=0)
        return qs.order_by('product__name')


class StockAdjustmentView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    template_name = 'inventory/adjust.html'
    form_class = StockAdjustmentForm
    success_url = reverse_lazy('inventory:overview')
    allowed_roles = UserRole.INVENTORY_TIER

    def form_valid(self, form):
        product = form.cleaned_data['product']
        trans_type = form.cleaned_data['transaction_type']
        quantity = form.cleaned_data['quantity']
        reason = form.cleaned_data['reason']
        notes = form.cleaned_data['notes']

        # Determine direction
        in_types = {InventoryTransactionType.PURCHASE, InventoryTransactionType.ADJUSTMENT_IN}
        direction = 1 if trans_type in in_types else -1

        try:
            entry = StockAdjustmentService.adjust_stock(
                product=product,
                quantity=quantity,
                direction=direction,
                transaction_type=trans_type,
                reason=reason,
                notes=notes,
                user=self.request.user
            )
            messages.success(
                self.request,
                f"Stock adjusted for {product.name}. New quantity: {entry.new_quantity}."
            )
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error adjusting stock: {str(e)}")
            return self.form_invalid(form)


class InventoryTransactionListView(LoginRequiredMixin, ListView):
    model = InventoryTransaction
    template_name = 'inventory/transactions.html'
    context_object_name = 'transactions'
    paginate_by = 30

    def get_queryset(self):
        qs = InventoryTransaction.objects.select_related('product', 'created_by').all()
        product_id = self.request.GET.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        trans_type = self.request.GET.get('type')
        if trans_type:
            qs = qs.filter(transaction_type=trans_type)
        return qs.order_by('-created_at')
