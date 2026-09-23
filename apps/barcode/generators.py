"""
Barcode generation strategies.
Decoupled strategies allow changing barcode format from StoreSettings without rewriting domain logic.
"""
from abc import ABC, abstractmethod
import random
import time
from apps.core.exceptions import DuplicateBarcodeError


class BarcodeGeneratorStrategy(ABC):
    """Abstract Strategy interface for barcode synthesis."""

    @abstractmethod
    def generate(self, seed: int = None) -> str:
        """Produce a formatted barcode string."""
        pass

    @abstractmethod
    def validate_format(self, value: str) -> bool:
        """Check whether value adheres to expected format."""
        pass


class InternalSequenceGenerator(BarcodeGeneratorStrategy):
    """
    Generates internal retail barcodes in the format: DZY-000000001
    Predictable, high-density, human readable.
    """
    def generate(self, seed: int = None) -> str:
        from apps.products.models import Product
        if seed is None:
            # Fallback based on maximum existing product ID + random jitter
            max_id = Product.all_objects.count() + 1
            seed = max_id
        return f"DZY-{seed:09d}"

    def validate_format(self, value: str) -> bool:
        return bool(value and value.startswith('DZY-') and len(value) == 13)


class Code128Generator(BarcodeGeneratorStrategy):
    """
    Standard Code 128 barcode generator.
    Produces high-density alphanumeric strings: DZ<Timestamp><Random>
    """
    def generate(self, seed: int = None) -> str:
        ts = int(time.time()) % 10000000
        rnd = random.randint(100, 999)
        return f"DZ{ts}{rnd}"

    def validate_format(self, value: str) -> bool:
        return bool(value and len(value) >= 6)


class EAN13Generator(BarcodeGeneratorStrategy):
    """
    EAN-13 barcode generator with modulo-10 check digit calculation.
    """
    def generate(self, seed: int = None) -> str:
        # Prefix 200 is standard GS1 in-store restricted distribution
        prefix = "200"
        core = f"{random.randint(100000000, 999999999)}"
        base12 = f"{prefix}{core}"[:12]
        check_digit = self._calculate_check_digit(base12)
        return f"{base12}{check_digit}"

    def validate_format(self, value: str) -> bool:
        if not value or len(value) != 13 or not value.isdigit():
            return False
        return int(value[-1]) == self._calculate_check_digit(value[:12])

    @staticmethod
    def _calculate_check_digit(digits12: str) -> int:
        odds = sum(int(d) for d in digits12[0::2])
        evens = sum(int(d) for d in digits12[1::2]) * 3
        total = odds + evens
        return (10 - (total % 10)) % 10
