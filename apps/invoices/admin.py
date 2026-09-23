from django.contrib import admin
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'sale', 'print_count', 'last_printed_at', 'created_at')
    search_fields = ('invoice_number', 'sale__customer_phone')
    readonly_fields = [f.name for f in Invoice._meta.fields]

    def has_add_permission(self, request):
        return False
