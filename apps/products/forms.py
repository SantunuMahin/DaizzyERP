from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    """
    Enhanced Product Form with elegant placeholders and luxury styling hooks.
    """
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'category', 'description', 'unit',
            'cost_price', 'selling_price', 'discount_price', 'minimum_stock_level', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Premium Cotton Casual Shirt',
                'autocomplete': 'off',
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. DZY-SHIRT-001',
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Scan or enter barcode (e.g. 8901234567890)',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the product specification, fabric, warranty, etc.',
                'rows': 3,
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. PCS, BOX, KG, LTR',
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00 (Optional promo price)',
                'step': '0.01',
                'min': '0',
            }),
            'minimum_stock_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 5',
                'min': '0',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
