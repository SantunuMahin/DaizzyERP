"""
Purchases & Procurement Services.
Handles stock addition, inventory ledger entry, product cost synchronization, and real-time purchase KPIs.
"""
from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from django.db.models import Sum, Count, F
from django.utils import timezone
from apps.products.models import Product
from apps.inventory.models import Inventory, InventoryTransaction, InventoryTransactionType
from .models import Purchase, PurchaseItem, PurchasePaymentStatus


class PurchaseService:

    @classmethod
    def generate_purchase_number(cls) -> str:
        """
        Generates sequential Purchase code: PUR-YYYYMM-00001
        """
        now = timezone.now()
        prefix = f"PUR-{now.strftime('%Y%m')}"
        last_pur = Purchase.objects.filter(purchase_number__startswith=prefix).order_by('-id').first()
        if last_pur and last_pur.purchase_number:
            try:
                seq = int(last_pur.purchase_number.split('-')[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"

    @classmethod
    @transaction.atomic
    def create_purchase(
        cls,
        supplier_name: str,
        items: List[Dict[str, Any]],
        supplier_phone: str = '',
        supplier_invoice: str = '',
        purchase_date=None,
        paid_amount: Decimal = Decimal('0.00'),
        payment_status: str = PurchasePaymentStatus.PAID,
        notes: str = '',
        created_by=None
    ) -> Purchase:
        """
        Atomically records a stock procurement order:
        1. Creates Purchase header.
        2. Records PurchaseItems.
        3. Atomically increases Inventory.quantity (O(1) fast lock).
        4. Writes immutable InventoryTransaction (PURCHASE).
        5. Optionally updates Product.cost_price to newest procurement cost.
        """
        if not items:
            raise ValueError("A purchase order must contain at least one product item.")

        if purchase_date is None:
            purchase_date = timezone.now().date()

        purchase_number = cls.generate_purchase_number()

        purchase = Purchase.objects.create(
            purchase_number=purchase_number,
            supplier_name=supplier_name.strip(),
            supplier_phone=supplier_phone.strip(),
            supplier_invoice=supplier_invoice.strip(),
            purchase_date=purchase_date,
            paid_amount=Decimal(str(paid_amount or '0.00')),
            payment_status=payment_status,
            notes=notes.strip(),
            created_by=created_by,
        )

        total_amount = Decimal('0.00')

        # Lock inventory rows for consistency
        product_ids = [it['product_id'] for it in items]
        inv_records = {inv.product_id: inv for inv in Inventory.objects.select_for_update().filter(product_id__in=product_ids)}

        for item_data in items:
            product_id = item_data['product_id']
            qty = int(item_data['quantity'])
            unit_cost = Decimal(str(item_data['unit_cost_price']))
            update_cost = bool(item_data.get('update_product_cost', True))

            if qty <= 0:
                continue

            product = Product.objects.get(pk=product_id)
            subtotal = unit_cost * Decimal(str(qty))
            total_amount += subtotal

            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                product_name=product.name,
                product_sku=product.sku,
                quantity=qty,
                unit_cost_price=unit_cost,
                subtotal=subtotal,
                update_product_cost=update_cost,
            )

            # Update master product cost price if selected
            if update_cost and unit_cost > 0:
                product.cost_price = unit_cost
                product.save(update_fields=['cost_price', 'updated_at'])

            # Increment stock in Inventory
            inv = inv_records.get(product.id)
            if not inv:
                inv = Inventory.objects.create(product=product, quantity=0)
                inv_records[product.id] = inv

            prev_qty = inv.quantity
            inv.quantity += qty
            inv.save(update_fields=['quantity', 'updated_at'])

            # Write stock transaction ledger
            InventoryTransaction.objects.create(
                product=product,
                transaction_type=InventoryTransactionType.PURCHASE,
                quantity=qty,
                direction=1,
                previous_quantity=prev_qty,
                new_quantity=inv.quantity,
                reference_type='purchase',
                reference_id=purchase.id,
                reason=f"Stock Purchase #{purchase.purchase_number} from {supplier_name}",
                created_by=created_by,
            )

        purchase.total_amount = total_amount
        if purchase.paid_amount >= total_amount:
            purchase.payment_status = PurchasePaymentStatus.PAID
        elif purchase.paid_amount > 0:
            purchase.payment_status = PurchasePaymentStatus.PARTIAL
        else:
            purchase.payment_status = PurchasePaymentStatus.DUE
        purchase.save(update_fields=['total_amount', 'payment_status', 'updated_at'])

        return purchase

    @classmethod
    def get_purchase_kpis(cls) -> Dict[str, Any]:
        """
        Calculates actionable real-time procurement KPIs:
        - Total lifetime purchases value
        - Today's purchases value & count
        - This month's purchases value & count
        - Total units purchased
        - Active supplier count
        """
        now = timezone.now()
        today = now.date()
        first_day_of_month = today.replace(day=1)

        # Lifetime
        all_purchases = Purchase.objects.all()
        total_spend = all_purchases.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        total_orders = all_purchases.count()

        # Today
        today_qs = all_purchases.filter(purchase_date=today)
        today_spend = today_qs.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        today_count = today_qs.count()

        # This Month
        month_qs = all_purchases.filter(purchase_date__gte=first_day_of_month, purchase_date__lte=today)
        this_month_spend = month_qs.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        this_month_count = month_qs.count()

        # Total units procured
        total_units = PurchaseItem.objects.aggregate(u=Sum('quantity'))['u'] or 0

        # Unique suppliers
        suppliers_count = all_purchases.values('supplier_name').distinct().count()

        return {
            'total_spend': total_spend,
            'total_orders': total_orders,
            'today_spend': today_spend,
            'today_count': today_count,
            'this_month_spend': this_month_spend,
            'this_month_count': this_month_count,
            'total_units': total_units,
            'suppliers_count': suppliers_count,
        }
