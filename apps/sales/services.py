"""
Sale and Return Service Layers.
Enforces atomic checkout, row-level inventory locking, price freezing, and stock restoration.
"""
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.products.models import Product
from apps.inventory.models import Inventory, InventoryTransaction, InventoryTransactionType
from apps.invoices.services import InvoiceService
from apps.core.exceptions import (
    InsufficientStockError,
    InvalidSaleOperationError,
    ReturnQuantityExceededError
)
from .models import Sale, SaleItem, Payment, Return, ReturnItem, SaleStatus, PaymentStatus

User = get_user_model()


class SaleService:
    """Orchestrates checkout, concurrency locks, payment, and invoice synthesis."""

    @classmethod
    def complete_sale(cls, items_data: list, payment_data: dict, cashier: User,
                      customer_data: dict = None, discount_amount: Decimal = Decimal('0.00'),
                      notes: str = '', idempotency_key: str = None) -> Sale:
        """
        Executes a complete atomic sale transaction.
        Guarantee:
          Sale + SaleItems + Payment + Inventory deduction + Ledger entries + Invoice
        """
        if not items_data:
            raise InvalidSaleOperationError("Cannot complete a sale with an empty cart.")

        customer_data = customer_data or {}
        discount_amount = Decimal(str(discount_amount or 0.00))

        # Check idempotency key if supplied
        if idempotency_key:
            existing_sale = Sale.objects.filter(idempotency_key=idempotency_key).first()
            if existing_sale:
                return existing_sale

        with transaction.atomic():
            product_ids = sorted(item['product_id'] for item in items_data)

            # Step 1: Row-level lock on inventory rows in deterministic order to prevent deadlocks
            inventories = (
                Inventory.objects
                .select_for_update()
                .filter(product_id__in=product_ids)
                .order_by('product_id')
            )
            inv_map = {inv.product_id: inv for inv in inventories}
            products_map = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

            # Step 2: Validate stock after acquiring row-level locks
            for item in items_data:
                p_id = item['product_id']
                qty = int(item['quantity'])
                inv = inv_map.get(p_id)
                if not inv or inv.quantity < qty:
                    available = inv.quantity if inv else 0
                    p_name = products_map[p_id].name if p_id in products_map else None
                    raise InsufficientStockError(p_id, available, qty, product_name=p_name)

            # Step 3: Compute totals
            subtotal = Decimal('0.00')
            processed_items = []
            for item in items_data:
                product = products_map[item['product_id']]
                qty = int(item['quantity'])
                unit_price = Decimal(str(item.get('unit_price', product.current_price)))
                item_discount = Decimal(str(item.get('discount', 0.00)))
                line_total = (unit_price * qty) - item_discount

                subtotal += line_total
                processed_items.append({
                    'product': product,
                    'unit_price': unit_price,
                    'discount': item_discount,
                    'quantity': qty,
                    'line_total': line_total,
                })

            grand_total = max(Decimal('0.00'), subtotal - discount_amount)
            amount_paid = Decimal(str(payment_data.get('amount_paid', grand_total)))
            change_amount = max(Decimal('0.00'), amount_paid - grand_total)

            # Step 4: Generate unique invoice number
            invoice_number = InvoiceService.generate_invoice_number()

            # Step 5: Resolve CRM Contact linkage
            contact_instance = None
            contact_id = customer_data.get('contact_id')
            c_phone = (customer_data.get('phone') or '').strip()
            c_name = (customer_data.get('name') or '').strip()
            c_email = (customer_data.get('email') or '').strip()

            try:
                from apps.messaging.models import Contact
                if contact_id:
                    contact_instance = Contact.objects.filter(id=contact_id).first()
                elif c_phone:
                    contact_instance = Contact.objects.filter(phone=c_phone).first() or \
                                       Contact.objects.filter(whatsapp_number=c_phone).first()

                # If online order and contact not found, auto-create Contact in CRM
                order_channel = customer_data.get('order_channel', 'POS')
                if not contact_instance and c_name and (c_phone or c_email) and order_channel != 'POS':
                    contact_instance = Contact.objects.create(
                        name=c_name,
                        phone=c_phone,
                        whatsapp_number=c_phone,
                        email=c_email,
                        notes=f"Auto-created from {order_channel} Order",
                    )
            except Exception as e:
                contact_instance = None

            # Step 5b: Create Sale record
            sale = Sale.objects.create(
                invoice_number=invoice_number,
                subtotal=subtotal,
                discount_amount=discount_amount,
                tax_amount=Decimal('0.00'),
                grand_total=grand_total,
                amount_paid=amount_paid,
                change_amount=change_amount,
                payment_status=PaymentStatus.PAID if amount_paid >= grand_total else PaymentStatus.PARTIAL,
                status=SaleStatus.COMPLETED,
                order_channel=customer_data.get('order_channel', 'POS'),
                contact=contact_instance,
                customer_name=c_name,
                customer_phone=c_phone,
                customer_email=c_email,
                delivery_address=customer_data.get('delivery_address', ''),
                delivery_notes=customer_data.get('delivery_notes', ''),
                courier_service=customer_data.get('courier_service', 'steadfast'),
                cashier=cashier,
                notes=notes,
                idempotency_key=idempotency_key,
            )

            # Step 6: Create SaleItems and deduct inventory atomically
            for p_item in processed_items:
                product = p_item['product']
                qty = p_item['quantity']

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    product_barcode=product.barcode,
                    unit_price=p_item['unit_price'],
                    discount=p_item['discount'],
                    quantity=qty,
                    line_total=p_item['line_total'],
                )

                inv = inv_map[product.id]
                prev_qty = inv.quantity
                inv.quantity -= qty
                inv.save(update_fields=['quantity', 'updated_at'])

                InventoryTransaction.objects.create(
                    product=product,
                    transaction_type=InventoryTransactionType.SALE,
                    quantity=qty,
                    direction=-1,
                    previous_quantity=prev_qty,
                    new_quantity=inv.quantity,
                    reference_type='sale',
                    reference_id=sale.id,
                    reason=f"Sale #{sale.invoice_number}",
                    created_by=cashier,
                )

            # Step 7: Record Payment
            Payment.objects.create(
                sale=sale,
                payment_method=payment_data.get('payment_method', 'CASH'),
                amount_paid=amount_paid,
                due_amount=max(Decimal('0.00'), grand_total - amount_paid),
                change_amount=change_amount,
                transaction_reference=payment_data.get('transaction_reference', ''),
                payment_status=sale.payment_status,
                notes=payment_data.get('notes', ''),
            )

            # Step 8: Create Invoice Snapshot
            InvoiceService.create_invoice(sale)

            # Step 9: Automatic Courier Dispatch for Online Orders (if enabled)
            should_auto_courier = customer_data.get('auto_dispatch_courier')
            if should_auto_courier is None:
                # Check CourierConfig default
                from apps.sales.courier.steadfast import SteadfastCourierService
                cfg = SteadfastCourierService.get_config()
                should_auto_courier = cfg.get('auto_send_on_confirm') and sale.is_online

            if should_auto_courier and sale.delivery_address:
                try:
                    cls.dispatch_to_steadfast(sale)
                except Exception as e:
                    pass

            # Step 10: Automated Customer Message Notification
            try:
                from apps.messaging.services.auto_messaging import AutoMessagingService
                AutoMessagingService.on_order_confirmed(sale)
            except Exception as e:
                pass

            return sale

    @classmethod
    def dispatch_to_steadfast(cls, sale, note: str = '') -> dict:
        """
        Dispatches an order to Steadfast Courier and updates consignment info.
        """
        from apps.sales.courier.steadfast import SteadfastCourierService
        from django.utils import timezone

        cod_amount = max(Decimal('0.00'), sale.grand_total - sale.amount_paid)
        # If order is fully paid online (e.g. bKash/Nagad), COD is 0
        if sale.payment_status == 'PAID':
            cod_amount = Decimal('0.00')

        recipient_name = sale.customer_name or 'Valued Customer'
        recipient_phone = sale.customer_phone or ''
        recipient_address = sale.delivery_address or 'Dhaka, Bangladesh'
        delivery_note = note or sale.delivery_notes or f"Invoice {sale.invoice_number}"

        result = SteadfastCourierService.create_order(
            invoice=sale.invoice_number,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            recipient_address=recipient_address,
            cod_amount=cod_amount,
            note=delivery_note,
        )

        consignment = result.get('consignment') or {}
        if consignment:
            sale.courier_service = 'steadfast'
            sale.courier_consignment_id = str(consignment.get('consignment_id', ''))
            sale.courier_tracking_code = str(consignment.get('tracking_code', ''))
            sale.courier_status = consignment.get('status', 'in_review')
            sale.courier_booked_at = timezone.now()
            sale.courier_response_raw = result
            sale.save(update_fields=[
                'courier_service', 'courier_consignment_id',
                'courier_tracking_code', 'courier_status',
                'courier_booked_at', 'courier_response_raw', 'updated_at'
            ])

            # Trigger automated courier dispatch message to customer
            try:
                from apps.messaging.services.auto_messaging import AutoMessagingService
                AutoMessagingService.on_courier_dispatched(sale)
            except Exception as e:
                pass

        return result

    @classmethod
    def sync_steadfast_status(cls, sale) -> dict:
        """
        Queries live Steadfast API for order status and updates sale record.
        """
        from apps.sales.courier.steadfast import SteadfastCourierService

        if not sale.courier_consignment_id and not sale.invoice_number:
            return {'error': True, 'message': 'No consignment or invoice found'}

        if sale.courier_consignment_id:
            result = SteadfastCourierService.get_status_by_cid(sale.courier_consignment_id)
        else:
            result = SteadfastCourierService.get_status_by_invoice(sale.invoice_number)

        delivery_status = result.get('delivery_status') or result.get('status')
        if delivery_status:
            status_map = {
                'in_review': 'in_review',
                'pending': 'pending',
                'in_transit': 'in_transit',
                'delivered': 'delivered',
                'partial_delivered': 'partial_delivered',
                'cancelled': 'cancelled',
            }
            new_status = status_map.get(delivery_status.lower(), sale.courier_status)
            sale.courier_status = new_status
            sale.save(update_fields=['courier_status', 'updated_at'])

            if new_status == 'delivered':
                try:
                    from apps.messaging.services.auto_messaging import AutoMessagingService
                    AutoMessagingService.on_order_delivered(sale)
                except Exception:
                    pass

        return result

    @classmethod
    @transaction.atomic
    def cancel_sale(cls, sale_id: int, reason: str, cancelled_by: User) -> Sale:
        """Rollback a completed sale and safely restore inventory."""
        sale = Sale.objects.select_for_update().get(id=sale_id)
        if sale.status != SaleStatus.COMPLETED:
            raise InvalidSaleOperationError(f"Cannot cancel sale in status {sale.status}")

        items = sale.items.select_related('product').all()
        for item in items:
            inv = Inventory.objects.select_for_update().get(product=item.product)
            prev_qty = inv.quantity
            inv.quantity += item.quantity
            inv.save(update_fields=['quantity', 'updated_at'])

            InventoryTransaction.objects.create(
                product=item.product,
                transaction_type=InventoryTransactionType.CORRECTION,
                quantity=item.quantity,
                direction=1,
                previous_quantity=prev_qty,
                new_quantity=inv.quantity,
                reference_type='sale_cancellation',
                reference_id=sale.id,
                reason=f"Cancellation of {sale.invoice_number}: {reason}",
                created_by=cancelled_by,
            )

        sale.status = SaleStatus.CANCELLED
        sale.save(update_fields=['status', 'updated_at'])
        return sale


class ReturnService:
    """Processes customer returns and restores inventory."""

    @classmethod
    @transaction.atomic
    def process_return(cls, sale_id: int, return_items_data: list, refund_method: str,
                       reason: str, notes: str = '', user: User = None) -> Return:
        sale = Sale.objects.get(id=sale_id)
        if sale.status not in (SaleStatus.COMPLETED, SaleStatus.PARTIALLY_RETURNED):
            raise InvalidSaleOperationError("Returns are only permitted on completed sales.")

        refund_total = Decimal('0.00')
        return_order = Return.objects.create(
            sale=sale,
            processed_by=user,
            refund_method=refund_method,
            reason=reason,
            notes=notes,
        )

        for r_item in return_items_data:
            sale_item_id = r_item['sale_item_id']
            qty = int(r_item['quantity'])

            sale_item = SaleItem.objects.get(id=sale_item_id, sale=sale)
            # Check previously returned quantity for this item
            prev_returned = ReturnItem.objects.filter(sale_item=sale_item).aggregate(
                models.Sum('quantity')
            )['quantity__sum'] or 0

            max_returnable = sale_item.quantity - prev_returned
            if qty > max_returnable:
                raise ReturnQuantityExceededError(
                    f"Cannot return {qty} items of '{sale_item.product_name}'. Max returnable: {max_returnable}"
                )

            item_refund = (sale_item.line_total / sale_item.quantity) * qty
            refund_total += item_refund

            ReturnItem.objects.create(
                return_order=return_order,
                sale_item=sale_item,
                product=sale_item.product,
                quantity=qty,
                unit_price=sale_item.unit_price,
                line_total=item_refund,
            )

            # Restore product inventory
            inv = Inventory.objects.select_for_update().get(product=sale_item.product)
            prev_qty = inv.quantity
            inv.quantity += qty
            inv.save(update_fields=['quantity', 'updated_at'])

            InventoryTransaction.objects.create(
                product=sale_item.product,
                transaction_type=InventoryTransactionType.RETURN,
                quantity=qty,
                direction=1,
                previous_quantity=prev_qty,
                new_quantity=inv.quantity,
                reference_type='return',
                reference_id=return_order.id,
                reason=f"Return on invoice #{sale.invoice_number}",
                created_by=user,
            )

        return_order.refund_amount = refund_total
        return_order.save(update_fields=['refund_amount'])

        # Update sale status
        total_items_sold = sum(i.quantity for i in sale.items.all())
        total_items_returned = sum(ri.quantity for ri in ReturnItem.objects.filter(sale_item__sale=sale))

        if total_items_returned >= total_items_sold:
            sale.status = SaleStatus.RETURNED
        else:
            sale.status = SaleStatus.PARTIALLY_RETURNED
        sale.save(update_fields=['status', 'updated_at'])

        return return_order
