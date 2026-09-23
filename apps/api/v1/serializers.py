"""
DRF Serializers for API v1.
"""
from rest_framework import serializers
from apps.products.models import Product, Category
from apps.inventory.models import Inventory, InventoryTransaction
from apps.sales.models import Sale, SaleItem, Payment, Return, ReturnItem
from apps.invoices.models import Invoice


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'image', 'display_priority')


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    current_stock = serializers.IntegerField(read_only=True)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'barcode', 'name', 'slug', 'category', 'category_name',
            'unit', 'selling_price', 'discount_price', 'current_price',
            'current_stock', 'minimum_stock_level', 'image', 'is_active'
        )


class ProductDetailSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ('description', 'cost_price', 'created_at', 'updated_at')


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    barcode = serializers.CharField(source='product.barcode', read_only=True)
    sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = Inventory
        fields = ('id', 'product', 'product_name', 'barcode', 'sku', 'quantity', 'updated_at')


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = (
            'id', 'product', 'product_name', 'product_sku', 'product_barcode',
            'unit_price', 'discount', 'quantity', 'line_total'
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id', 'payment_method', 'amount_paid', 'due_amount',
            'change_amount', 'transaction_reference', 'payment_status'
        )


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    cashier_username = serializers.CharField(source='cashier.username', read_only=True)

    class Meta:
        model = Sale
        fields = (
            'id', 'invoice_number', 'subtotal', 'discount_amount', 'tax_amount',
            'grand_total', 'amount_paid', 'change_amount', 'payment_status',
            'status', 'cashier', 'cashier_username', 'customer_name',
            'customer_phone', 'customer_email', 'notes', 'items', 'payment',
            'created_at'
        )


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'invoice_number', 'sale', 'print_count', 'last_printed_at', 'created_at')
