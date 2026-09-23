"""
Barcode printing and preview views.
"""
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404
from apps.products.models import Product
from .services import BarcodeService


class BarcodePrintLabelsView(LoginRequiredMixin, TemplateView):
    """
    Thermal/Sticker Label Printing View.
    Allows batch label generation with product name, SKU, price, and barcode.
    """
    template_name = 'barcode/print_labels.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product_ids = self.request.GET.getlist('products')
        quantity = int(self.request.GET.get('qty', 1))

        products = []
        if product_ids:
            products = Product.objects.filter(id__in=product_ids, is_active=True)
        else:
            single_id = self.request.GET.get('product')
            if single_id:
                products = Product.objects.filter(id=single_id, is_active=True)

        items_to_print = []
        for p in products:
            svg_data = BarcodeService.render_svg(p.barcode)
            for _ in range(quantity):
                items_to_print.append({
                    'product': p,
                    'svg': svg_data,
                })

        ctx['items_to_print'] = items_to_print
        ctx['all_products'] = Product.objects.filter(is_active=True).order_by('name')
        return ctx


class BarcodeImageServeView(LoginRequiredMixin, View):
    """Returns SVG directly for dynamic barcode rendering."""
    def get(self, request, barcode_value):
        try:
            svg_content = BarcodeService.render_svg(barcode_value)
            return HttpResponse(svg_content, content_type='image/svg+xml')
        except Exception:
            raise Http404("Invalid barcode value.")
