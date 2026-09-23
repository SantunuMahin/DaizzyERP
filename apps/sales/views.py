"""
Sales history, details, cancellation, and returns views.
"""
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
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
