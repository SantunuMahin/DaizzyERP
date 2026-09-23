"""
Store and POS operational configuration models.
"""
from django.db import models


class StoreSettings(models.Model):
    """
    Singleton operational settings for Daizzy.online.
    Controls business identifiers, receipt printing widths, and barcode policy.
    """
    store_name = models.CharField(max_length=200, default='Daizzy.online')
    store_address = models.TextField(blank=True, default='Dhaka, Bangladesh')
    phone = models.CharField(max_length=30, blank=True, default='+880 1700-000000')
    email = models.EmailField(blank=True, default='contact@daizzy.online')
    website = models.URLField(blank=True, default='https://daizzy.online')
    logo = models.ImageField(upload_to='store/', blank=True, null=True)

    currency = models.CharField(max_length=10, default='BDT')
    currency_symbol = models.CharField(max_length=5, default='৳')

    invoice_prefix = models.CharField(max_length=20, default='INV')
    invoice_number_format = models.CharField(
        max_length=100,
        default='{prefix}-{year}-{seq:06d}',
        help_text="Template for invoice code generation"
    )

    barcode_format = models.CharField(
        max_length=30,
        choices=[
            ('INTERNAL', 'Internal Sequential (DZY-000000001)'),
            ('CODE128', 'Code 128 Standard'),
            ('EAN13', 'EAN-13 (GS1 compatible)'),
        ],
        default='INTERNAL'
    )

    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    default_discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    allow_negative_stock = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveSmallIntegerField(default=5)
    receipt_width_mm = models.PositiveSmallIntegerField(
        choices=[(58, '58 mm Thermal'), (80, '80 mm Thermal')],
        default=80
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Store Settings'
        verbose_name_plural = 'Store Settings'

    def __str__(self):
        return f"{self.store_name} Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton pattern (only one instance permitted)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Retrieve or initialize the active singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
