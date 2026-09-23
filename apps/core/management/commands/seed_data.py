"""
Seed command to populate initial demonstration data for Daizzy IMS.
Directly aligned with https://www.daizzy.online (Curated Lifestyle & Self-Care Store).
Usage: python manage.py seed_data
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.permissions import UserRole
from apps.settings_app.models import StoreSettings
from apps.products.models import Category, Product
from apps.inventory.services import StockAdjustmentService
from apps.inventory.models import InventoryTransactionType
from apps.sales.services import SaleService
from apps.sales.models import PaymentMethod

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds database with realistic retail sample data for Daizzy.online'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting Daizzy IMS database seeding..."))

        # 1. Initialize Store Settings based on www.daizzy.online
        settings = StoreSettings.get_settings()
        settings.store_name = 'Daizzy.online'
        settings.store_address = 'House 14, Road 5, Dhanmondi, Dhaka, Bangladesh'
        settings.phone = '+8801631009941'
        settings.email = 'support@daizzy.online'
        settings.website = 'https://daizzy.online'
        settings.currency = 'BDT'
        settings.currency_symbol = '৳'
        settings.barcode_format = 'INTERNAL'
        settings.save()
        self.stdout.write(self.style.SUCCESS("[OK] Store Settings initialized (Daizzy.online)"))

        # 2. Create Users
        users_data = [
            ('admin', 'admin@daizzy.online', 'admin123456', UserRole.SUPER_ADMIN, 'Super', 'Admin', True),
            ('manager', 'manager@daizzy.online', 'manager123456', UserRole.MANAGER, 'Sarah', 'Ahmed', True),
            ('cashier', 'cashier@daizzy.online', 'cashier123456', UserRole.CASHIER, 'Rahim', 'Uddin', False),
            ('inventory_mgr', 'inventory@daizzy.online', 'inv123456', UserRole.INVENTORY_MANAGER, 'Karim', 'Hossain', False),
        ]

        user_instances = {}
        for username, email, pwd, role, first, last, staff in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'role': role,
                    'first_name': first,
                    'last_name': last,
                    'is_staff': staff,
                    'is_superuser': (role == UserRole.SUPER_ADMIN),
                }
            )
            if created:
                user.set_password(pwd)
                user.save()
            user_instances[username] = user
        self.stdout.write(self.style.SUCCESS(f"[OK] Users initialized ({len(users_data)} roles)"))

        # 3. Create Categories based on daizzy.online curated catalog
        categories_data = [
            ("Pipe Cleaner Bouquets", "pipe-cleaner-bouquets", "Handcrafted pipe cleaner floral arrangements & bouquets", 1),
            ("Flower Renu & Adornments", "flower-renu-adornments", "Artisan flower renu, hair garlands, and floral brooch pins", 2),
            ("DIY Craft Kits & Materials", "diy-craft-kits", "Pipe cleaners, craft stems, wires, florist tape & DIY kits", 3),
            ("Self-Care & Wellness", "self-care-wellness", "Hand-poured scented candles, aromatherapy, and facial mists", 4),
            ("Custom Gift Packages", "custom-gift-packages", "Artisan gift hampers, celebration boxes, and partner finds", 5),
        ]

        cat_instances = {}
        for name, slug, desc, prio in categories_data:
            cat, _ = Category.all_objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': desc, 'display_priority': prio, 'is_active': True}
            )
            cat_instances[slug] = cat
        self.stdout.write(self.style.SUCCESS(f"[OK] Categories created ({len(categories_data)})"))

        # 4. Create Products & Initial Stock Ledger based on daizzy.online
        products_data = [
            ("Pastel Daisy Pipe Cleaner Bouquet", "FLW-DSY-001", "DZY-000000001", "pipe-cleaner-bouquets", 380.00, 750.00, 690.00, 35),
            ("Lavender & Tulip Handcrafted Bouquet", "FLW-TLP-002", "DZY-000000002", "pipe-cleaner-bouquets", 650.00, 1250.00, None, 25),
            ("Sunshine Sunflower Table Arrangement", "FLW-SNF-003", "DZY-000000003", "pipe-cleaner-bouquets", 480.00, 950.00, 890.00, 20),
            ("Artisan Flower Renu Hair Garland", "REN-GAR-004", "DZY-000000004", "flower-renu-adornments", 220.00, 480.00, None, 40),
            ("Ceramic Floral Brooch Pin", "REN-BRC-005", "DZY-000000005", "flower-renu-adornments", 110.00, 250.00, 220.00, 4), # Low stock!
            ("Deluxe Pastel Pipe Cleaners (Pack of 100)", "DIY-KIT-006", "DZY-000000006", "diy-craft-kits", 320.00, 650.00, None, 50),
            ("Florist Stem Wires & Ribbon Craft Pack", "DIY-STM-007", "DZY-000000007", "diy-craft-kits", 120.00, 280.00, None, 0), # Out of stock!
            ("Organic Lavender Soy Scented Candle", "CND-LAV-008", "DZY-000000008", "self-care-wellness", 420.00, 850.00, None, 30),
            ("Rosewater Hydrating Botanical Mist", "SKN-MST-009", "DZY-000000009", "self-care-wellness", 340.00, 690.00, 620.00, 45),
            ("Celebration Custom Gift Hamper Box", "PKG-CEL-010", "DZY-000000010", "custom-gift-packages", 1300.00, 2450.00, 2250.00, 12),
        ]

        product_instances = []
        admin_user = user_instances['admin']

        for name, sku, barcode, cat_slug, cost, price, discount, initial_stock in products_data:
            prod, created = Product.all_objects.get_or_create(
                barcode=barcode,
                defaults={
                    'sku': sku,
                    'name': name,
                    'slug': sku.lower(),
                    'category': cat_instances[cat_slug],
                    'cost_price': Decimal(str(cost)),
                    'selling_price': Decimal(str(price)),
                    'discount_price': Decimal(str(discount)) if discount else None,
                    'minimum_stock_level': 5,
                    'is_active': True,
                }
            )
            # If product existed from previous seed with older name/category, update it:
            if not created:
                prod.name = name
                prod.category = cat_instances[cat_slug]
                prod.cost_price = Decimal(str(cost))
                prod.selling_price = Decimal(str(price))
                prod.discount_price = Decimal(str(discount)) if discount else None
                prod.save()

            product_instances.append(prod)

            if created and initial_stock > 0:
                # Add opening stock via Ledger Service
                StockAdjustmentService.adjust_stock(
                    product=prod,
                    quantity=initial_stock,
                    direction=1,
                    transaction_type=InventoryTransactionType.OPENING_STOCK,
                    reason="Initial Catalog Inventory Opening Stock",
                    notes="Automated system seed initialization",
                    user=admin_user,
                    reference_type='system_seed'
                )

        self.stdout.write(self.style.SUCCESS(f"[OK] Products created with dual-write ledger stock ({len(products_data)})"))

        # 5. Simulate 2 Completed Initial Sales to populate orders, payments, invoices
        cashier = user_instances['cashier']

        # Sale 1: Rahim sells Daisy Bouquet and Renu Brooch to walk-in customer
        cart1 = [
            {'product_id': product_instances[0].id, 'quantity': 1, 'unit_price': product_instances[0].current_price},
            {'product_id': product_instances[4].id, 'quantity': 1, 'unit_price': product_instances[4].current_price},
        ]
        payment1 = {'payment_method': PaymentMethod.CASH, 'amount_paid': Decimal('1000.00')}
        customer1 = {'name': 'Tasnim Anjum', 'phone': '01812345678', 'email': 'tasnim@example.com'}

        sale1 = SaleService.complete_sale(
            items_data=cart1,
            payment_data=payment1,
            cashier=cashier,
            customer_data=customer1,
            notes="In-store boutique purchase"
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Simulated Sale #1 completed: {sale1.invoice_number} ({sale1.grand_total} BDT)"))

        # Sale 2: Sarah sells Lavender Bouquet to bKash customer
        cart2 = [
            {'product_id': product_instances[1].id, 'quantity': 1, 'unit_price': product_instances[1].current_price},
        ]
        payment2 = {
            'payment_method': PaymentMethod.BKASH,
            'amount_paid': product_instances[1].current_price,
            'transaction_reference': 'BK89712635B'
        }
        customer2 = {'name': 'Nusrat Jahan', 'phone': '01798765432'}

        sale2 = SaleService.complete_sale(
            items_data=cart2,
            payment_data=payment2,
            cashier=user_instances['manager'],
            customer_data=customer2,
            discount_amount=Decimal('50.00'),
            notes="Lifestyle gift promotion"
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Simulated Sale #2 completed: {sale2.invoice_number} ({sale2.grand_total} BDT)"))

        self.stdout.write(self.style.SUCCESS("\n==> DAIZZY IMS SEEDING COMPLETE! Ready for retail operation."))
