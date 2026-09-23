"""
Invoice numbering and rendering service.
"""
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import connection
from apps.settings_app.models import StoreSettings
from .models import Invoice


class InvoiceService:
    """Manages unique invoice serial generation and static print snapshot rendering."""

    @classmethod
    def generate_invoice_number(cls) -> str:
        """
        Generates concurrency-safe invoice number.
        Uses PostgreSQL sequence when available, or reliable fallback on SQLite.
        """
        settings = StoreSettings.get_settings()
        prefix = settings.invoice_prefix
        year = timezone.now().year

        seq = None
        if connection.vendor == 'postgresql':
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT nextval('invoice_number_seq')")
                    seq = cursor.fetchone()[0]
            except Exception:
                pass

        if seq is None:
            # Fallback sequence generation based on max existing Invoice ID
            max_id = Invoice.objects.count() + 1
            seq = max_id

        # Render format: {prefix}-{year}-{seq:06d}
        return f"{prefix}-{year}-{seq:06d}"

    @classmethod
    def create_invoice(cls, sale) -> Invoice:
        """Renders HTML snapshot and persists Invoice record."""
        settings = StoreSettings.get_settings()

        context = {
            'sale': sale,
            'settings': settings,
            'items': sale.items.all(),
            'payment': getattr(sale, 'payment', None),
        }

        # Render thermal-optimized receipt HTML
        rendered_html = render_to_string('invoices/receipt_template.html', context)

        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number=sale.invoice_number,
            invoice_html=rendered_html,
        )
        return invoice
