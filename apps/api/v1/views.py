"""
REST API v1 ViewSets and Endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.products.models import Product, Category
from apps.inventory.models import Inventory
from apps.sales.models import Sale
from apps.invoices.models import Invoice
from apps.sales.services import SaleService
from apps.core.permissions import IsCashierOrAbove, IsReadOnlyOrAdmin
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, CategorySerializer,
    InventorySerializer, SaleSerializer, InvoiceSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True).order_by('display_priority', 'name')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related('category', 'inventory').filter(is_active=True).order_by('name')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=False, methods=['get'], url_path='barcode/(?P<barcode>[^/.]+)')
    def by_barcode(self, request, barcode=None):
        """POS fast path: lookup product by barcode."""
        product = get_object_or_404(
            Product.objects.select_related('category', 'inventory').filter(is_active=True),
            barcode=barcode
        )
        serializer = ProductListSerializer(product)
        return Response({'success': True, 'data': serializer.data})


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inventory.objects.select_related('product').filter(product__is_active=True)
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related('cashier', 'payment').prefetch_related('items').all().order_by('-created_at')
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, IsCashierOrAbove]

    def create(self, request, *args, **kwargs):
        """
        Execute POS sale checkout via API.
        Expected payload:
        {
          "items": [{"product_id": 1, "quantity": 2, "unit_price": 450.00}],
          "payment": {"payment_method": "CASH", "amount_paid": 900.00},
          "customer": {"name": "...", "phone": "..."},
          "discount_amount": 0.00,
          "notes": ""
        }
        """
        data = request.data
        items_data = data.get('items', [])
        payment_data = data.get('payment', {})
        customer_data = data.get('customer', {})
        discount_amount = data.get('discount_amount', 0.00)
        notes = data.get('notes', '')
        idempotency_key = request.headers.get('X-Idempotency-Key') or data.get('idempotency_key')

        sale = SaleService.complete_sale(
            items_data=items_data,
            payment_data=payment_data,
            cashier=request.user,
            customer_data=customer_data,
            discount_amount=discount_amount,
            notes=notes,
            idempotency_key=idempotency_key,
        )

        serializer = SaleSerializer(sale)
        return Response({
            'success': True,
            'data': serializer.data,
            'invoice_number': sale.invoice_number,
        }, status=status.HTTP_201_CREATED)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.select_related('sale').all().order_by('-created_at')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
