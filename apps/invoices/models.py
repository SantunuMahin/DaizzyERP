"""
Invoice model and frozen presentation snapshot.
"""
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    """
    Generated commercial invoice for a completed sale.
    Stores pre-rendered HTML snapshot to guarantee reprint fidelity.
    """
    sale = models.OneToOneField('sales.Sale', on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_html = models.TextField(blank=True, help_text="Pixel-accurate rendered HTML snapshot")
    print_count = models.PositiveSmallIntegerField(default=0)
    last_printed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def record_print(self):
        self.print_count += 1
        self.last_printed_at = timezone.now()
        self.save(update_fields=['print_count', 'last_printed_at'])
