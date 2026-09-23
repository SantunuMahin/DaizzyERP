"""
Views for Product and Category catalog management.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .models import Product, Category


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.select_related('category', 'inventory').filter(is_active=True)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(barcode__icontains=search) | qs.filter(sku__icontains=search)
        category_id = self.request.GET.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs.order_by('name')


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx['inventory_transactions'] = self.object.inventory_transactions.select_related('created_by').order_by('-created_at')[:15]
        except Exception:
            ctx['inventory_transactions'] = []
        return ctx


class ProductCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Product
    fields = [
        'name', 'sku', 'barcode', 'category', 'description', 'unit',
        'cost_price', 'selling_price', 'discount_price', 'minimum_stock_level', 'image'
    ]
    template_name = 'products/create.html'
    success_url = reverse_lazy('products:list')
    allowed_roles = UserRole.INVENTORY_TIER

    def form_valid(self, form):
        response = super().form_valid(form)
        # Ensure Inventory record is initialized
        from apps.inventory.models import Inventory
        Inventory.objects.get_or_create(product=self.object, defaults={'quantity': 0})
        messages.success(self.request, f"Product '{self.object.name}' created.")
        return response


class ProductUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Product
    fields = [
        'name', 'sku', 'barcode', 'category', 'description', 'unit',
        'cost_price', 'selling_price', 'discount_price', 'minimum_stock_level', 'image'
    ]
    template_name = 'products/edit.html'
    allowed_roles = UserRole.INVENTORY_TIER

    def get_success_url(self):
        return reverse_lazy('products:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Product '{self.object.name}' updated.")
        return super().form_valid(form)
