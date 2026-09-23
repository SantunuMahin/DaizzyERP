from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_priority', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'category', 'selling_price', 'current_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku', 'barcode')
    prepopulated_fields = {'slug': ('name',)}
