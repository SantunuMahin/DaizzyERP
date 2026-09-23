"""
Sales, SaleItems, Payments, and Returns models.
Historical pricing and product details are frozen at point of sale.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.products.models import Product
import uuid


class PaymentMethod:
    CASH = 'CASH'
    BKASH = 'BKASH'
    NAGAD = 'NAGAD'
    CARD = 'CARD'
    BANK = 'BANK'
    OTHER = 'OTHER'

    CHOICES = [
        (CASH, 'Cash'),
        (BKASH, 'bKash Mobile Wallet'),
        (NAGAD, 'Nagad Mobile Wallet'),
        (CARD, 'Credit/Debit Card'),
        (BANK, 'Direct Bank Transfer'),
        (OTHER, 'Other / Split'),
    ]


class PaymentStatus:
    PENDING = 'PENDING'
    PAID = 'PAID'
    PARTIAL = 'PARTIAL'
    REFUNDED = 'REFUNDED'

    CHOICES = [
        (PENDING, 'Pending Payment'),
        (PAID, 'Fully Paid'),
        (PARTIAL, 'Partially Paid'),
        (REFUNDED, 'Refunded'),
    ]


class SaleStatus:
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    PARTIALLY_RETURNED = 'PARTIALLY_RETURNED'
    RETURNED = 'RETURNED'

    CHOICES = [
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (PARTIALLY_RETURNED, 'Partially Returned'),
        (RETURNED, 'Fully Returned'),
    ]


class OrderChannel:
    POS = 'POS'
    ONLINE = 'ONLINE'
    WHATSAPP = 'WHATSAPP'
    MESSENGER = 'MESSENGER'
    TELEGRAM = 'TELEGRAM'
    PHONE = 'PHONE'
    OTHER = 'OTHER'

    CHOICES = [
        (POS, 'In-Store POS'),
        (ONLINE, 'Online Order'),
        (WHATSAPP, 'WhatsApp Order'),
        (MESSENGER, 'Facebook Messenger'),
        (TELEGRAM, 'Telegram Order'),
        (PHONE, 'Phone Call'),
        (OTHER, 'Other Channel'),
    ]


class CourierStatus:
    NONE = 'none'
    PENDING = 'pending'
    IN_REVIEW = 'in_review'
    IN_TRANSIT = 'in_transit'
    DELIVERED = 'delivered'
    PARTIAL_DELIVERED = 'partial_delivered'
    CANCELLED = 'cancelled'

    CHOICES = [
        (NONE, 'Not Dispatched'),
        (PENDING, 'Pending Pickup'),
        (IN_REVIEW, 'In Review (Steadfast)'),
        (IN_TRANSIT, 'In Transit / On the Way'),
        (DELIVERED, 'Delivered Successfully'),
        (PARTIAL_DELIVERED, 'Partially Delivered'),
        (CANCELLED, 'Cancelled / Returned'),
    ]


class CourierConfig(models.Model):
    """Configuration for Steadfast and other logistics partners."""
    courier_name = models.CharField(max_length=50, default='steadfast', unique=True)
    display_name = models.CharField(max_length=100, default='Steadfast Courier')
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255, blank=True, verbose_name='API Key')
    secret_key = models.CharField(max_length=255, blank=True, verbose_name='Secret Key')
    base_url = models.URLField(default='https://portal.steadfast.com.bd/api/v1', verbose_name='Base URL')
    auto_send_on_confirm = models.BooleanField(default=True, help_text='Automatically book parcel on Steadfast when order is confirmed')
    test_mode = models.BooleanField(default=False, help_text='Simulate responses without real API calls')
    webhook_secret = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Courier Configuration'
        verbose_name_plural = 'Courier Configurations'

    def __str__(self):
        return f"{self.display_name} ({'Active' if self.is_active else 'Inactive'})"


class Sale(models.Model):
    """
    Primary Sales Order Entity.
    Represents an immutable commercial sale record.
    """
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PAID,
        db_index=True
    )
    status = models.CharField(
        max_length=25,
        choices=SaleStatus.CHOICES,
        default=SaleStatus.COMPLETED,
        db_index=True
    )

    # Omnichannel and CRM linkage
    order_channel = models.CharField(
        max_length=20,
        choices=OrderChannel.CHOICES,
        default=OrderChannel.POS,
        db_index=True
    )
    contact = models.ForeignKey(
        'messaging.Contact',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders',
        help_text='Linked customer contact from Messaging Hub'
    )

    # Customer and Delivery details
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)
    customer_email = models.EmailField(blank=True)
    delivery_address = models.TextField(blank=True, verbose_name='Delivery Street Address')
    delivery_notes = models.CharField(max_length=300, blank=True, verbose_name='Delivery Notes / Instructions')

    # Steadfast Courier Integration fields
    courier_service = models.CharField(max_length=50, default='steadfast')
    courier_consignment_id = models.CharField(max_length=100, blank=True, db_index=True)
    courier_tracking_code = models.CharField(max_length=100, blank=True, db_index=True)
    courier_status = models.CharField(
        max_length=30,
        choices=CourierStatus.CHOICES,
        default=CourierStatus.NONE,
        db_index=True
    )
    courier_booked_at = models.DateTimeField(null=True, blank=True)
    courier_response_raw = models.JSONField(default=dict, blank=True)

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales'
    )
    notes = models.TextField(blank=True)

    # Idempotency token to protect against accidental duplicate checkout submissions
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} | {self.grand_total} BDT"

    @property
    def is_online(self):
        return self.order_channel in (OrderChannel.ONLINE, OrderChannel.WHATSAPP, OrderChannel.MESSENGER, OrderChannel.TELEGRAM)

    @property
    def tracking_url(self):
        if self.courier_tracking_code:
            return f"https://steadfast.com.bd/t/{self.courier_tracking_code}"
        return ''

    @property
    def due_amount(self):
        return max(Decimal('0.00'), self.grand_total - self.amount_paid)


class SaleItem(models.Model):
    """
    Line Item of a Sale.
    Snapshots product information and pricing at point of sale.
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')

    product_name = models.CharField(max_length=300)
    product_sku = models.CharField(max_length=100)
    product_barcode = models.CharField(max_length=100)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    quantity = models.PositiveSmallIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} = {self.line_total}"


class Payment(models.Model):
    """Payment transaction details for a sale."""
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.CHOICES, default=PaymentMethod.CASH)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    transaction_reference = models.CharField(max_length=200, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.CHOICES, default=PaymentStatus.PAID)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.payment_method}: {self.amount_paid} BDT"


class Return(models.Model):
    """Customer merchandise return and inventory restoration."""
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_returns'
    )
    refund_method = models.CharField(max_length=30, choices=PaymentMethod.CHOICES, default=PaymentMethod.CASH)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    reason = models.CharField(max_length=300)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='COMPLETED')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Return'
        verbose_name_plural = 'Returns'
        ordering = ['-created_at']

    def __str__(self):
        return f"Return #{self.id} for Invoice {self.sale.invoice_number}"


class ReturnItem(models.Model):
    """Line item of a merchandise return."""
    return_order = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name='return_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Return Item'
        verbose_name_plural = 'Return Items'
