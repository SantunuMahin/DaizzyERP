"""
Inventory state and movement ledger models.
Dual-write pattern: cached quantity for O(1) POS checks + immutable transaction ledger.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.products.models import Product


class InventoryTransactionType:
    OPENING_STOCK = 'OPENING_STOCK'
    PURCHASE = 'PURCHASE'
    SALE = 'SALE'
    RETURN = 'RETURN'
    ADJUSTMENT_IN = 'ADJUSTMENT_IN'
    ADJUSTMENT_OUT = 'ADJUSTMENT_OUT'
    DAMAGE = 'DAMAGE'
    LOSS = 'LOSS'
    CORRECTION = 'CORRECTION'

    CHOICES = [
        (OPENING_STOCK, 'Opening Stock'),
        (PURCHASE, 'Stock Addition (Purchase)'),
        (SALE, 'POS Sale Deduction'),
        (RETURN, 'Sales Return Inward'),
        (ADJUSTMENT_IN, 'Manual Adjustment (Increase)'),
        (ADJUSTMENT_OUT, 'Manual Adjustment (Decrease)'),
        (DAMAGE, 'Damaged Inventory'),
        (LOSS, 'Lost / Stolen Stock'),
        (CORRECTION, 'Inventory Count Correction'),
    ]


class Inventory(models.Model):
    """
    Denormalized current product stock quantity.
    Row is locked during sale checkout with select_for_update() to prevent race conditions.
    """
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory',
        db_index=True
    )
    quantity = models.IntegerField(default=0, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f"{self.product.name}: {self.quantity} units"


class InventoryTransaction(models.Model):
    """
    Immutable Auditable Stock Ledger.
    Every single inventory alteration must record a corresponding ledger entry.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_transactions',
        db_index=True
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=InventoryTransactionType.CHOICES,
        db_index=True
    )
    quantity = models.PositiveIntegerField(help_text="Volume of items moved (always positive)")
    direction = models.SmallIntegerField(
        choices=[(1, 'IN (+)'), (-1, 'OUT (-)')],
        help_text="+1 for stock addition, -1 for deduction"
    )
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    reference_type = models.CharField(max_length=50, blank=True, help_text="e.g. sale, return, adjustment")
    reference_id = models.BigIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_transactions'
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True, editable=False)

    class Meta:
        verbose_name = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        sign = '+' if self.direction > 0 else '-'
        return f"{self.product.name} | {self.transaction_type} | {sign}{self.quantity} ({self.previous_quantity} -> {self.new_quantity})"
