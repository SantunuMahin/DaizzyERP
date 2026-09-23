"""
Barcode Service Layer.
Enforces unique product barcode invariants and handles SVG rendering.
"""
import io
import barcode
from barcode.writer import SVGWriter, ImageWriter
from apps.settings_app.models import StoreSettings
from apps.products.models import Product
from apps.core.exceptions import DuplicateBarcodeError
from .generators import (
    BarcodeGeneratorStrategy,
    InternalSequenceGenerator,
    Code128Generator,
    EAN13Generator
)


class BarcodeService:
    """Central business operations relating to product barcodes."""

    @classmethod
    def get_strategy(cls) -> BarcodeGeneratorStrategy:
        """Instantiate generator based on active StoreSettings format."""
        fmt = StoreSettings.get_settings().barcode_format
        if fmt == 'CODE128':
            return Code128Generator()
        elif fmt == 'EAN13':
            return EAN13Generator()
        return InternalSequenceGenerator()

    @classmethod
    def generate_unique_barcode(cls, max_retries: int = 10) -> str:
        """Generate a barcode guaranteed not to conflict with any existing product."""
        strategy = cls.get_strategy()
        for _ in range(max_retries):
            code = strategy.generate()
            if not Product.all_objects.filter(barcode=code).exists():
                return code
        raise RuntimeError("Unable to generate unique barcode after multiple attempts.")

    @classmethod
    def validate_uniqueness(cls, barcode_value: str, exclude_product_id: int = None) -> bool:
        """Verify barcode is not in use by any other product."""
        qs = Product.all_objects.filter(barcode=barcode_value)
        if exclude_product_id:
            qs = qs.exclude(pk=exclude_product_id)
        if qs.exists():
            raise DuplicateBarcodeError(barcode_value)
        return True

    @classmethod
    def render_svg(cls, barcode_value: str) -> str:
        """Generate printable SVG XML string for a barcode value."""
        code128 = barcode.get('code128', barcode_value, writer=SVGWriter())
        buffer = io.BytesIO()
        code128.write(buffer, options={
            'write_text': True,
            'module_width': 0.25,
            'module_height': 12.0,
            'font_size': 10,
            'text_distance': 4.0,
            'quiet_zone': 2.0,
        })
        return buffer.getvalue().decode('utf-8')

    @classmethod
    def lookup_product(cls, barcode_value: str) -> Product:
        """Fast product lookup by exact barcode (POS critical path)."""
        return Product.objects.select_related('inventory', 'category').get(
            barcode=barcode_value.strip(),
            is_active=True
        )
