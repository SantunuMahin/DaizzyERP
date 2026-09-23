"""
Messaging-to-Order Connection & Quick Order Views.
Allows staff to create sales orders directly from customer conversations,
sync order history, and control Steadfast Courier dispatches.
"""
import json
import logging
from decimal import Decimal
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages as flash_messages

from apps.messaging.models import Contact, Conversation
from apps.sales.models import Sale, PaymentMethod
from apps.sales.services import SaleService
from apps.sales.courier.steadfast import SteadfastCourierService
from apps.products.models import Product

logger = logging.getLogger(__name__)


class QuickOrderCreateView(LoginRequiredMixin, View):
    """
    Create a sales order directly from the Messaging Inbox or Contact Profile.
    Locks row-level inventory, deductions, creates invoice, books Steadfast (if chosen),
    and sends automated confirmation on the messaging channel.
    """

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'

        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except Exception:
                data = {}
        else:
            data = request.POST

        contact_id = data.get('contact_id')
        contact = get_object_or_404(Contact, pk=contact_id) if contact_id else None

        # Process item rows
        items_data = []
        raw_items = data.get('items')
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except Exception:
                raw_items = []

        if raw_items and isinstance(raw_items, list):
            for it in raw_items:
                p_id = it.get('product_id')
                qty = int(it.get('quantity', 1))
                if p_id and qty > 0:
                    product = Product.objects.filter(pk=p_id).first()
                    if product:
                        unit_p = Decimal(str(it.get('unit_price') or product.current_price))
                        items_data.append({
                            'product_id': product.pk,
                            'quantity': qty,
                            'unit_price': unit_p,
                            'discount': Decimal(str(it.get('discount', 0.00))),
                        })
        else:
            # Fallback for simple single product form
            product_id = data.get('product_id')
            qty = int(data.get('quantity', 1))
            if product_id:
                product = get_object_or_404(Product, pk=product_id)
                items_data.append({
                    'product_id': product.pk,
                    'quantity': qty,
                    'unit_price': Decimal(str(data.get('unit_price') or product.current_price)),
                    'discount': Decimal('0.00'),
                })

        if not items_data:
            err = "Please select at least one product with quantity."
            if is_ajax:
                return JsonResponse({'success': False, 'error': err}, status=400)
            flash_messages.error(request, err)
            return redirect(request.META.get('HTTP_REFERER', '/messaging/inbox/'))

        # Prepare customer and delivery data
        delivery_address = data.get('delivery_address', '').strip()
        delivery_notes = data.get('delivery_notes', '').strip()
        order_channel = data.get('order_channel', 'ONLINE')
        payment_method = data.get('payment_method', PaymentMethod.CASH)
        amount_paid = Decimal(str(data.get('amount_paid', '0.00') or '0.00'))
        auto_courier = str(data.get('auto_dispatch_courier', 'true')).lower() in ('true', '1', 'on')

        customer_data = {
            'contact_id': contact.pk if contact else None,
            'name': contact.name if contact else data.get('customer_name', 'Customer'),
            'phone': contact.phone or contact.whatsapp_number if contact else data.get('customer_phone', ''),
            'email': contact.email if contact else data.get('customer_email', ''),
            'order_channel': order_channel,
            'delivery_address': delivery_address,
            'delivery_notes': delivery_notes,
            'auto_dispatch_courier': auto_courier,
            'courier_service': 'steadfast',
        }

        payment_data = {
            'payment_method': payment_method,
            'amount_paid': amount_paid,
            'transaction_reference': data.get('transaction_reference', ''),
            'notes': data.get('payment_notes', ''),
        }

        try:
            sale = SaleService.complete_sale(
                items_data=items_data,
                payment_data=payment_data,
                cashier=request.user,
                customer_data=customer_data,
                discount_amount=Decimal(str(data.get('discount_amount', '0.00') or '0.00')),
                notes=data.get('order_notes', f"Created from Messaging Hub via {order_channel}"),
            )

            msg_text = f"Order #{sale.invoice_number} created successfully ({sale.grand_total} BDT)!"
            if sale.courier_consignment_id:
                msg_text += f" Booked on Steadfast (Tracking: {sale.courier_tracking_code})."

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': msg_text,
                    'invoice_number': sale.invoice_number,
                    'sale_id': sale.pk,
                    'grand_total': str(sale.grand_total),
                    'tracking_code': sale.courier_tracking_code,
                    'tracking_url': sale.tracking_url,
                })

            flash_messages.success(request, msg_text)
            return redirect(f"/sales/{sale.pk}/")

        except Exception as e:
            logger.error(f"QuickOrder creation failed: {e}", exc_info=True)
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            flash_messages.error(request, f"Could not create order: {str(e)}")
            return redirect(request.META.get('HTTP_REFERER', '/messaging/inbox/'))


class ContactOrdersAPIView(LoginRequiredMixin, View):
    """
    Returns JSON list of orders and lifetime stats for a contact.
    Used for instant dynamic rendering in Chat sidebar and modals.
    """

    def get(self, request, contact_id):
        contact = get_object_or_404(Contact, pk=contact_id)
        orders = Sale.objects.filter(contact=contact).order_by('-created_at')

        # Also fallback by phone if orders were created by phone before linking
        if not orders.exists() and contact.phone:
            orders = Sale.objects.filter(customer_phone=contact.phone).order_by('-created_at')

        total_spent = sum(o.grand_total for o in orders)
        total_orders = orders.count()

        orders_data = [{
            'id': o.pk,
            'invoice_number': o.invoice_number,
            'date': o.created_at.strftime('%d %b %Y, %H:%M'),
            'grand_total': float(o.grand_total),
            'amount_paid': float(o.amount_paid),
            'payment_status': o.get_payment_status_display(),
            'status': o.get_status_display(),
            'order_channel': o.get_order_channel_display(),
            'courier_service': o.courier_service,
            'courier_status': o.get_courier_status_display(),
            'courier_tracking_code': o.courier_tracking_code,
            'tracking_url': o.tracking_url,
            'items_count': o.items.count(),
            'detail_url': f"/sales/{o.pk}/",
        } for o in orders[:15]]

        return JsonResponse({
            'contact_id': contact.pk,
            'contact_name': contact.name,
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'orders': orders_data,
        })


class SteadfastDispatchActionView(LoginRequiredMixin, View):
    """
    Manual trigger to dispatch an order to Steadfast Courier.
    """

    def post(self, request, sale_id):
        sale = get_object_or_404(Sale, pk=sale_id)
        note = request.POST.get('note', '')

        try:
            result = SaleService.dispatch_to_steadfast(sale, note=note)
            if result.get('status') == 200 or 'consignment' in result:
                flash_messages.success(
                    request,
                    f"Consignment booked on Steadfast! Consignment ID: {sale.courier_consignment_id}, Tracking: {sale.courier_tracking_code}"
                )
            else:
                flash_messages.warning(
                    request,
                    f"Steadfast response: {result.get('message', 'Booking status recorded.')}"
                )
        except Exception as e:
            flash_messages.error(request, f"Failed to book Steadfast consignment: {str(e)}")

        return redirect(f"/sales/{sale.pk}/")


class SteadfastStatusSyncActionView(LoginRequiredMixin, View):
    """
    Sync live delivery status directly from Steadfast Courier API.
    """

    def post(self, request, sale_id):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        sale = get_object_or_404(Sale, pk=sale_id)

        try:
            result = SaleService.sync_steadfast_status(sale)
            msg = f"Status updated: {sale.get_courier_status_display()}"
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'courier_status': sale.courier_status,
                    'status_display': sale.get_courier_status_display(),
                    'message': msg,
                })
            flash_messages.success(request, msg)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            flash_messages.error(request, f"Error checking Steadfast status: {str(e)}")

        return redirect(f"/sales/{sale.pk}/")


class SteadfastBalanceView(LoginRequiredMixin, View):
    """
    Check Steadfast Account Balance.
    """

    def get(self, request):
        balance_info = SteadfastCourierService.get_account_balance()
        return JsonResponse(balance_info)
