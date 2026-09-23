from django import forms
from .models import StoreSettings


class StoreSettingsForm(forms.ModelForm):
    """
    Enhanced Store Settings Form with modern attributes, classes, and placeholder styling.
    """
    class Meta:
        model = StoreSettings
        fields = [
            'store_name', 'store_address', 'phone', 'email', 'website', 'logo',
            'currency', 'currency_symbol', 'invoice_prefix', 'invoice_number_format',
            'barcode_format', 'default_tax_rate', 'default_discount_rate',
            'allow_negative_stock', 'low_stock_threshold', 'receipt_width_mm'
        ]
        widgets = {
            'store_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Daizzy.online Store',
                'autocomplete': 'organization',
            }),
            'store_address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter complete physical address (e.g. House 14, Road 5, Dhanmondi, Dhaka)',
                'rows': 3,
                'autocomplete': 'street-address',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +880 1631-009941',
                'autocomplete': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. support@daizzy.online',
                'autocomplete': 'email',
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. https://daizzy.online',
                'autocomplete': 'url',
            }),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. BDT',
            }),
            'currency_symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. ৳ or $',
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 5',
                'min': '0',
            }),
            'default_tax_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'default_discount_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'barcode_format': forms.Select(attrs={
                'class': 'form-select',
            }),
            'receipt_width_mm': forms.Select(attrs={
                'class': 'form-select',
            }),
            'invoice_prefix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. DZ or INV',
            }),
            'invoice_number_format': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. {prefix}-{year}-{seq:06d}',
            }),
            'allow_negative_stock': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
