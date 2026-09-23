"""
Service layer for inventory management and ledger updates.
"""
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.products.models import Product
from apps.settings_app.models import StoreSettings
from apps.core.exceptions import InsufficientStockError
from .models import Inventory, InventoryTransaction, InventoryTransactionType

User = get_user_model()


class StockAdjustmentService:
    """Handles controlled manual stock modifications and ledger logging."""

    @staticmethod
    @transaction.atomic
    def adjust_stock(product: Product, quantity: int, direction: int,
                     transaction_type: str, reason: str, notes: str = '',
                     user: User = None, reference_type: str = 'adjustment',
                     reference_id: int = None) -> InventoryTransaction:
        """
        Atomically alters product inventory and writes ledger audit entry.
        direction: +1 for addition, -1 for deduction.
        """
        if quantity <= 0:
            raise ValueError("Adjustment quantity must be greater than zero.")
        if direction not in (-1, 1):
            raise ValueError("Direction must be either +1 (IN) or -1 (OUT).")

        # Acquire row-level lock on Inventory row
        inventory, _ = Inventory.objects.select_for_update().get_or_create(
            product=product,
            defaults={'quantity': 0}
        )

        previous_quantity = inventory.quantity
        delta = quantity * direction
        new_quantity = previous_quantity + delta

        settings = StoreSettings.get_settings()
        if new_quantity < 0 and not settings.allow_negative_stock:
            raise InsufficientStockError(product.id, previous_quantity, quantity)

        # Update denormalized quantity
        inventory.quantity = new_quantity
        inventory.save(update_fields=['quantity', 'updated_at'])

        # Create immutable ledger record
        ledger_entry = InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=quantity,
            direction=direction,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            notes=notes,
            created_by=user,
        )

        return ledger_entry


class InventoryService:
    """Query service for stock inquiries."""

    @staticmethod
    def get_stock(product_id: int) -> int:
        try:
            return Inventory.objects.get(product_id=product_id).quantity
        except Inventory.DoesNotExist:
            return 0

    @staticmethod
    def get_low_stock_products():
        threshold = StoreSettings.get_settings().low_stock_threshold
        return Product.objects.filter(
            is_active=True,
            inventory__quantity__lte=threshold
        ).select_related('inventory', 'category')
