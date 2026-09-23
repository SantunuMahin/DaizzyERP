"""
Invoice presentation and print views.
"""
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Invoice


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'invoices/list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = Invoice.objects.select_related('sale', 'sale__cashier').all()
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(invoice_number__icontains=query) | qs.filter(sale__customer_phone__icontains=query)
        return qs.order_by('-created_at')


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'invoices/detail.html'
    context_object_name = 'invoice'


class InvoicePrintView(LoginRequiredMixin, View):
    """
    Renders standalone thermal receipt page and records print event.
    """
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.record_print()

        # If snapshot exists, serve it; otherwise render on the fly
        if invoice.invoice_html:
            return HttpResponse(invoice.invoice_html)

        from apps.settings_app.models import StoreSettings
        from django.template.loader import render_to_string
        context = {
            'sale': invoice.sale,
            'settings': StoreSettings.get_settings(),
            'items': invoice.sale.items.all(),
            'payment': getattr(invoice.sale, 'payment', None),
        }
        html = render_to_string('invoices/receipt_template.html', context)
        return HttpResponse(html)
