"""
Product Catalog Models for Daizzy IMS.
"""
from django.db import models
from django.utils.text import slugify
from apps.core.models import SoftDeleteModel, TimeStampedModel


class Category(SoftDeleteModel):
    """Product hierarchical or flat categorization."""
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    display_priority = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['display_priority', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(SoftDeleteModel):
    """
    Sellable Product Entity.
    The barcode and SKU are uniquely constrained at the database level.
    """
    sku = models.CharField(max_length=100, unique=True, db_index=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique Barcode (Code128 / EAN-13 / Internal)"
    )
    name = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default='pcs')

    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    minimum_stock_level = models.PositiveSmallIntegerField(default=5)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} [{self.barcode}]"

    @property
    def current_price(self):
        """Effective sale price considering discounts."""
        if self.discount_price and self.discount_price > 0 and self.discount_price < self.selling_price:
            return self.discount_price
        return self.selling_price

    @property
    def current_stock(self):
        """Current stock count from linked inventory."""
        try:
            return self.inventory.quantity
        except Exception:
            return 0

    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock_level

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0
