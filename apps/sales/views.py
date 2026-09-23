"""
Sales history, details, cancellation, and returns views.
"""
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .models import Sale, Return
from .services import SaleService, ReturnService


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/list.html'
    context_object_name = 'sales'
    paginate_by = 25

    def get_queryset(self):
        qs = Sale.objects.select_related('cashier', 'payment', 'contact').all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(invoice_number__icontains=q) | qs.filter(customer_phone__icontains=q) | qs.filter(customer_name__icontains=q)
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        channel_filter = self.request.GET.get('channel')
        if channel_filter:
            if channel_filter == 'online':
                qs = qs.exclude(order_channel='POS')
            else:
                qs = qs.filter(order_channel=channel_filter)
        courier_filter = self.request.GET.get('courier_status')
        if courier_filter:
            qs = qs.filter(courier_status=courier_filter)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['channel_filter'] = self.request.GET.get('channel', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['courier_filter'] = self.request.GET.get('courier_status', '')
        ctx['online_count'] = Sale.objects.exclude(order_channel='POS').count()
        ctx['pos_count'] = Sale.objects.filter(order_channel='POS').count()
        return ctx


class SaleCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Create a new Sales Order / Online Delivery Order with direct Steadfast Courier dispatch.
    """
    template_name = 'sales/create.html'
    allowed_roles = UserRole.CASHIER_TIER

    def get(self, request):
        from apps.products.models import Product
        from apps.messaging.models import Contact
        from .models import PaymentMethod, OrderChannel
        from .courier.steadfast import SteadfastCourierService

        products = Product.objects.filter(is_active=True).select_related('category', 'inventory').order_by('name')
        contacts = Contact.objects.all().order_by('-updated_at')[:20]
        cfg = SteadfastCourierService.get_config()

        return render(request, self.template_name, {
            'products': products,
            'contacts': contacts,
            'payment_methods': PaymentMethod.CHOICES,
            'channels': OrderChannel.CHOICES,
            'courier_config': cfg,
        })

    def post(self, request):
        from decimal import Decimal
        from apps.products.models import Product

        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_email = request.POST.get('customer_email', '').strip()
        delivery_address = request.POST.get('delivery_address', '').strip()
        delivery_notes = request.POST.get('delivery_notes', '').strip()
        order_channel = request.POST.get('order_channel', 'ONLINE')
        payment_method = request.POST.get('payment_method', 'CASH')
        amount_paid_raw = request.POST.get('amount_paid', '0.00')
        dispatch_courier = request.POST.get('dispatch_courier') in ('on', 'true', '1')
        notes = request.POST.get('notes', '').strip()

        # Parse item rows
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')
        discounts = request.POST.getlist('discount[]')

        items_data = []
        for idx in range(len(product_ids)):
            p_id = product_ids[idx]
            if not p_id:
                continue
            try:
                qty = int(quantities[idx])
                price = Decimal(str(unit_prices[idx]))
                disc = Decimal(str(discounts[idx])) if idx < len(discounts) and discounts[idx] else Decimal('0.00')
                if qty > 0 and price >= 0:
                    items_data.append({
                        'product_id': int(p_id),
                        'quantity': qty,
                        'unit_price': price,
                        'discount': disc,
                    })
            except (ValueError, IndexError):
                continue

        if not items_data:
            messages.error(request, "Please add at least one product with valid quantity and price.")
            return redirect('sales:create')

        amount_paid = Decimal(amount_paid_raw or '0.00')

        customer_data = {
            'name': customer_name or 'Online Customer',
            'phone': customer_phone,
            'email': customer_email,
            'order_channel': order_channel,
            'delivery_address': delivery_address,
            'delivery_notes': delivery_notes,
            'auto_dispatch_courier': dispatch_courier,
            'courier_service': 'steadfast' if dispatch_courier else 'none',
        }

        payment_data = {
            'payment_method': payment_method,
            'amount_paid': amount_paid,
            'transaction_reference': request.POST.get('transaction_reference', ''),
            'notes': request.POST.get('payment_notes', ''),
        }

        try:
            sale = SaleService.create_sale(
                items_data=items_data,
                payment_data=payment_data,
                cashier=request.user,
                customer_data=customer_data,
                notes=notes,
            )

            # If courier dispatch was selected, check if dispatch succeeded or do direct call
            if dispatch_courier:
                if not sale.courier_consignment_id:
                    try:
                        SaleService.dispatch_to_steadfast(sale, note=delivery_notes)
                        sale.refresh_from_db()
                    except Exception as e:
                        messages.warning(request, f"Order #{sale.invoice_number} created, but courier dispatch note: {str(e)}")

                if sale.courier_consignment_id:
                    messages.success(
                        request,
                        f"Order #{sale.invoice_number} created & booked in Steadfast Courier! Tracking Code: {sale.courier_tracking_code}"
                    )
                else:
                    messages.success(request, f"Order #{sale.invoice_number} created successfully.")
            else:
                messages.success(request, f"Order #{sale.invoice_number} created successfully.")

            return redirect('sales:detail', pk=sale.pk)
        except Exception as e:
            messages.error(request, f"Failed to create order: {str(e)}")
            return redirect('sales:create')


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/detail.html'
    context_object_name = 'sale'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('product').all()
        ctx['returns'] = self.object.returns.prefetch_related('items').all()
        return ctx


class SaleCancelView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Cancels a sale and restores stock (Manager+ only)."""
    allowed_roles = UserRole.MANAGER_TIER

    def post(self, request, pk):
        reason = request.POST.get('reason', 'Administrative cancellation')
        try:
            SaleService.cancel_sale(sale_id=pk, reason=reason, cancelled_by=request.user)
            messages.success(request, "Sale cancelled successfully. Inventory has been restored.")
        except Exception as e:
            messages.error(request, f"Cannot cancel sale: {str(e)}")
        return redirect('sales:detail', pk=pk)


class ReturnListView(LoginRequiredMixin, ListView):
    model = Return
    template_name = 'sales/returns_list.html'
    context_object_name = 'returns'
    paginate_by = 25

    def get_queryset(self):
        return Return.objects.select_related('sale', 'processed_by').all().order_by('-created_at')


class CourierSettingsView(LoginRequiredMixin, View):
    """Steadfast Courier API settings and balance lookup."""
    template_name = 'sales/courier_settings.html'

    def get(self, request):
        from .models import CourierConfig
        from .courier.steadfast import SteadfastCourierService
        cfg, _ = CourierConfig.objects.get_or_create(
            courier_name='steadfast',
            defaults={
                'display_name': 'Steadfast Courier',
                'base_url': 'https://portal.steadfast.com.bd/api/v1',
                'auto_send_on_confirm': True,
                'test_mode': False,
            }
        )
        balance_info = SteadfastCourierService.get_account_balance()
        return render(request, self.template_name, {
            'page_title': 'Steadfast Courier Settings',
            'config': cfg,
            'balance_info': balance_info,
        })

    def post(self, request):
        from .models import CourierConfig
        cfg, _ = CourierConfig.objects.get_or_create(courier_name='steadfast')
        cfg.api_key = request.POST.get('api_key', '').strip()
        cfg.secret_key = request.POST.get('secret_key', '').strip()
        cfg.base_url = request.POST.get('base_url', 'https://portal.steadfast.com.bd/api/v1').strip()
        cfg.is_active = request.POST.get('is_active') == 'on'
        cfg.auto_send_on_confirm = request.POST.get('auto_send_on_confirm') == 'on'
        cfg.test_mode = request.POST.get('test_mode') == 'on'
        cfg.save()

        messages.success(request, 'Steadfast Courier configuration updated successfully.')
        return redirect('sales:courier_settings')


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
import json

@method_decorator(csrf_exempt, name='dispatch')
class SteadfastWebhookView(View):
    """
    Receives real-time parcel delivery status updates pushed by Steadfast Courier.
    """
    def post(self, request):
        try:
            payload = json.loads(request.body)
        except Exception:
            payload = request.POST.dict()

        consignment_id = str(payload.get('consignment_id') or payload.get('cid') or '').strip()
        invoice = str(payload.get('invoice') or payload.get('invoice_number') or '').strip()
        new_status = str(payload.get('status') or payload.get('delivery_status') or '').strip().lower()

        if not new_status:
            return JsonResponse({'error': 'Missing status'}, status=400)

        sale = None
        if consignment_id:
            sale = Sale.objects.filter(courier_consignment_id=consignment_id).first()
        if not sale and invoice:
            sale = Sale.objects.filter(invoice_number=invoice).first()

        if sale:
            status_map = {
                'in_review': 'in_review',
                'pending': 'pending',
                'in_transit': 'in_transit',
                'delivered': 'delivered',
                'partial_delivered': 'partial_delivered',
                'cancelled': 'cancelled',
            }
            mapped_status = status_map.get(new_status, sale.courier_status)
            sale.courier_status = mapped_status
            sale.save(update_fields=['courier_status', 'updated_at'])

            if mapped_status == 'delivered':
                try:
                    from apps.messaging.services.auto_messaging import AutoMessagingService
                    AutoMessagingService.on_order_delivered(sale)
                except Exception:
                    pass

            return JsonResponse({'success': True, 'invoice': sale.invoice_number, 'status': sale.courier_status})

        return JsonResponse({'message': 'Webhook received, no matching order found'}, status=200)
