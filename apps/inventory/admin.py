from django.contrib import admin
from .models import Inventory, InventoryTransaction


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'updated_at')
    search_fields = ('product__name', 'product__sku', 'product__barcode')


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'direction', 'previous_quantity', 'new_quantity', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'direction', 'created_at')
    search_fields = ('product__name', 'product__barcode', 'reason')
    readonly_fields = [f.name for f in InventoryTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
