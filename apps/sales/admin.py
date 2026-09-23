from django.contrib import admin
from .models import Sale, SaleItem, Payment, Return, ReturnItem, CourierConfig


@admin.register(CourierConfig)
class CourierConfigAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'courier_name', 'is_active', 'auto_send_on_confirm', 'test_mode', 'updated_at')
    list_filter = ('is_active', 'auto_send_on_confirm', 'test_mode')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = [f.name for f in SaleItem._meta.fields]


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = [f.name for f in Payment._meta.fields]


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order_channel', 'customer_name', 'customer_phone', 'grand_total', 'payment_status', 'courier_status', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'order_channel', 'courier_status', 'created_at')
    search_fields = ('invoice_number', 'customer_phone', 'customer_name', 'courier_tracking_code')
    inlines = [SaleItemInline, PaymentInline]
    readonly_fields = [f.name for f in Sale._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale', 'refund_amount', 'refund_method', 'processed_by', 'created_at')
    readonly_fields = [f.name for f in Return._meta.fields]

    def has_add_permission(self, request):
        return False
