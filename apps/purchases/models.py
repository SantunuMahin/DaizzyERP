"""
Purchase and Procurement Models.
Tracks incoming inventory stock purchases, supplier invoices, cost breakdown, and procurement KPIs.
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.products.models import Product


class PurchasePaymentStatus:
    PAID = 'PAID'
    PARTIAL = 'PARTIAL'
    DUE = 'DUE'

    CHOICES = [
        (PAID, 'Fully Paid'),
        (PARTIAL, 'Partially Paid'),
        (DUE, 'Payment Due'),
    ]


class Purchase(models.Model):
    """
    Stock Procurement & Purchase Order Header.
    """
    purchase_number = models.CharField(max_length=50, unique=True, db_index=True)
    supplier_name = models.CharField(max_length=200, db_index=True, help_text="Supplier or vendor name")
    supplier_phone = models.CharField(max_length=50, blank=True, help_text="Contact number")
    supplier_invoice = models.CharField(max_length=100, blank=True, help_text="External vendor invoice / challan number")
    purchase_date = models.DateField(default=timezone.now, db_index=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(
        max_length=20,
        choices=PurchasePaymentStatus.CHOICES,
        default=PurchasePaymentStatus.PAID,
        db_index=True
    )

    notes = models.TextField(blank=True, help_text="Procurement notes, terms, or remarks")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_purchases'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock Purchase'
        verbose_name_plural = 'Stock Purchases'
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f"{self.purchase_number} - {self.supplier_name} ({self.total_amount})"

    @property
    def due_amount(self) -> Decimal:
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items.all())


class PurchaseItem(models.Model):
    """
    Itemized products procured in a Purchase order.
    """
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(help_text="Units procured")
    unit_cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price per unit")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    update_product_cost = models.BooleanField(
        default=True,
        help_text="Automatically update product cost_price to this procurement unit price"
    )

    class Meta:
        verbose_name = 'Purchase Item'
        verbose_name_plural = 'Purchase Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} @ {self.unit_cost_price}"

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.name
        if not self.product_sku and self.product:
            self.product_sku = self.product.sku
        if not self.subtotal:
            self.subtotal = Decimal(str(self.quantity)) * self.unit_cost_price
        super().save(*args, **kwargs)
