"""
Core Domain & Business Invariants Test Suite.
Verifies barcode uniqueness, dual-write stock ledger, checkout invariants, and API contracts.
"""
from decimal import Decimal
import uuid
from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.permissions import UserRole
from apps.products.models import Product, Category
from apps.inventory.models import Inventory, InventoryTransaction, InventoryTransactionType
from apps.inventory.services import StockAdjustmentService
from apps.sales.models import Sale, PaymentMethod, SaleStatus
from apps.sales.services import SaleService
from apps.core.exceptions import InsufficientStockError

User = get_user_model()


class BusinessInvariantsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cashier = User.objects.create_user(
            username='cashier_tester',
            email='cashier_tester@test.com',
            password='testpassword123',
            role=UserRole.CASHIER
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            sku='TEST-SKU-001',
            barcode='DZY-999000001',
            name='Test Cotton Shirt',
            slug='test-cotton-shirt',
            category=self.category,
            cost_price=Decimal('200.00'),
            selling_price=Decimal('500.00'),
            minimum_stock_level=5,
        )
        # Give initial stock of 10 units via StockAdjustmentService
        StockAdjustmentService.adjust_stock(
            product=self.product,
            quantity=10,
            direction=1,
            transaction_type=InventoryTransactionType.OPENING_STOCK,
            reason="Opening Stock Setup",
            user=self.cashier
        )

    def test_barcode_uniqueness_enforced_at_db_level(self):
        """Rule 2 & 67: Every sellable product must have a unique barcode enforced at DB level."""
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                sku='DIFF-SKU-002',
                barcode='DZY-999000001',  # Duplicate barcode!
                name='Duplicate Barcode Item',
                slug='dup-item',
                category=self.category,
                selling_price=Decimal('300.00')
            )

    def test_inventory_ledger_dual_write_accuracy(self):
        """Rule 7 & 13: Stock quantity and movement ledger remain consistent."""
        inv = Inventory.objects.get(product=self.product)
        self.assertEqual(inv.quantity, 10)

        # Apply manual damage deduction
        entry = StockAdjustmentService.adjust_stock(
            product=self.product,
            quantity=3,
            direction=-1,
            transaction_type=InventoryTransactionType.DAMAGE,
            reason="Water damage during storage",
            user=self.cashier
        )

        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 7)
        self.assertEqual(entry.previous_quantity, 10)
        self.assertEqual(entry.new_quantity, 7)
        self.assertEqual(entry.direction, -1)

    def test_sale_fails_on_insufficient_stock(self):
        """Rule 8 & 14: Protection against negative stock and overselling."""
        cart = [{'product_id': self.product.id, 'quantity': 15, 'unit_price': 500.00}]
        payment = {'payment_method': PaymentMethod.CASH, 'amount_paid': Decimal('7500.00')}

        with self.assertRaises(InsufficientStockError):
            SaleService.complete_sale(
                items_data=cart,
                payment_data=payment,
                cashier=self.cashier
            )

        # Verify stock was not touched
        inv = Inventory.objects.get(product=self.product)
        self.assertEqual(inv.quantity, 10)

    def test_complete_sale_invariants(self):
        """
        Rule 66 Invariant:
        Completed sale = Sale + SaleItems + Payment + Invoice + Inventory deduction + Ledger entry
        """
        cart = [{'product_id': self.product.id, 'quantity': 2, 'unit_price': Decimal('500.00')}]
        payment = {'payment_method': PaymentMethod.CASH, 'amount_paid': Decimal('1000.00')}

        sale = SaleService.complete_sale(
            items_data=cart,
            payment_data=payment,
            cashier=self.cashier,
            customer_data={'name': 'Customer A', 'phone': '01700000000'}
        )

        # 1. Sale record created with invoice number
        self.assertIsNotNone(sale.invoice_number)
        self.assertEqual(sale.status, SaleStatus.COMPLETED)
        self.assertEqual(sale.grand_total, Decimal('1000.00'))

        # 2. SaleItems created and price snapshotted
        items = sale.items.all()
        self.assertEqual(items.count(), 1)
        item = items.first()
        self.assertEqual(item.unit_price, Decimal('500.00'))
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.line_total, Decimal('1000.00'))

        # 3. Inventory deducted
        inv = Inventory.objects.get(product=self.product)
        self.assertEqual(inv.quantity, 8)

        # 4. Ledger entry logged
        last_ledger = InventoryTransaction.objects.filter(product=self.product).order_by('-created_at').first()
        self.assertEqual(last_ledger.transaction_type, InventoryTransactionType.SALE)
        self.assertEqual(last_ledger.quantity, 2)
        self.assertEqual(last_ledger.direction, -1)
        self.assertEqual(last_ledger.previous_quantity, 10)
        self.assertEqual(last_ledger.new_quantity, 8)

        # 5. Invoice created with HTML snapshot
        self.assertIsNotNone(sale.invoice)
        self.assertTrue(len(sale.invoice.invoice_html) > 50)
        self.assertEqual(sale.invoice.invoice_number, sale.invoice_number)

    def test_sale_idempotency_prevents_duplicate_deduction(self):
        """Rule 14: Client idempotency key prevents double submissions."""
        key = uuid.uuid4()
        cart = [{'product_id': self.product.id, 'quantity': 1, 'unit_price': Decimal('500.00')}]
        payment = {'payment_method': PaymentMethod.CASH, 'amount_paid': Decimal('500.00')}

        # First checkout attempt
        sale1 = SaleService.complete_sale(
            items_data=cart,
            payment_data=payment,
            cashier=self.cashier,
            idempotency_key=key
        )

        # Immediate retry with same key (e.g. user double-clicked)
        sale2 = SaleService.complete_sale(
            items_data=cart,
            payment_data=payment,
            cashier=self.cashier,
            idempotency_key=key
        )

        self.assertEqual(sale1.id, sale2.id)
        # Stock should only be deducted once (10 - 1 = 9)
        inv = Inventory.objects.get(product=self.product)
        self.assertEqual(inv.quantity, 9)

    def test_rest_api_barcode_lookup(self):
        """Rule 9 & 26: REST API fast barcode lookup."""
        self.client.force_authenticate(user=self.cashier)
        url = f"/api/v1/products/barcode/{self.product.barcode}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['barcode'], self.product.barcode)
        self.assertEqual(response.data['data']['current_stock'], 10)
