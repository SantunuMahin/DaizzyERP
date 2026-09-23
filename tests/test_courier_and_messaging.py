"""
Tests for Steadfast Courier Integration, Customer Messaging-to-Order Bridge,
and Automated Messaging Engine.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.products.models import Product, Category
from apps.inventory.models import Inventory
from apps.messaging.models import Contact, Conversation, Message, Platform
from apps.sales.models import Sale, OrderChannel, CourierStatus, CourierConfig
from apps.sales.services import SaleService
from apps.sales.courier.steadfast import SteadfastCourierService
from apps.messaging.services.auto_messaging import AutoMessagingService

User = get_user_model()


class CourierAndAutoMessagingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_test',
            email='admin@daizzy.online',
            password='TestPassword123!',
            role='ADMIN'
        )

        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Wireless Earbuds Pro',
            sku='EAR-PRO-001',
            barcode='8941234567890',
            cost_price=Decimal('1200.00'),
            current_price=Decimal('1850.00'),
            category=self.category,
            is_active=True
        )

        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=50,
            reorder_threshold=5
        )

        self.contact = Contact.objects.create(
            name='Tanvir Ahmed',
            phone='01711223344',
            whatsapp_number='01711223344',
            email='tanvir@example.com',
            notes='House 14, Road 7, Banani, Dhaka'
        )

        self.courier_config = CourierConfig.objects.create(
            courier_name='steadfast',
            display_name='Steadfast Courier',
            is_active=True,
            auto_send_on_confirm=True,
            test_mode=True
        )

    def test_steadfast_courier_service_simulation(self):
        """Test Steadfast Courier client order creation in simulation mode."""
        resp = SteadfastCourierService.create_order(
            invoice='INV-TEST-001',
            recipient_name='Tanvir Ahmed',
            recipient_phone='+8801711223344',
            recipient_address='Banani, Dhaka',
            cod_amount=Decimal('1850.00'),
            note='Fragile delivery'
        )

        self.assertEqual(resp.get('status'), 200)
        self.assertIn('consignment', resp)
        consignment = resp['consignment']
        self.assertTrue(consignment['tracking_code'].startswith('STDF'))
        self.assertEqual(consignment['invoice'], 'INV-TEST-001')

    def test_steadfast_status_and_balance(self):
        """Test status lookup and account balance checks."""
        status_resp = SteadfastCourierService.get_status_by_cid('C123456')
        self.assertEqual(status_resp.get('status'), 200)
        self.assertEqual(status_resp.get('delivery_status'), 'in_transit')

        bal_resp = SteadfastCourierService.get_account_balance()
        self.assertEqual(bal_resp.get('status'), 200)
        self.assertGreater(bal_resp.get('current_balance', 0), 0)

    def test_complete_sale_with_contact_and_steadfast_dispatch(self):
        """Test creating an online order linked to a messaging contact with auto-dispatch."""
        items_data = [{
            'product_id': self.product.id,
            'quantity': 2,
            'unit_price': self.product.current_price,
            'discount': Decimal('0.00'),
        }]

        payment_data = {
            'payment_method': 'CASH',
            'amount_paid': Decimal('0.00'),  # full COD
        }

        customer_data = {
            'contact_id': self.contact.id,
            'name': self.contact.name,
            'phone': self.contact.phone,
            'order_channel': OrderChannel.WHATSAPP,
            'delivery_address': 'House 14, Road 7, Banani, Dhaka',
            'auto_dispatch_courier': True,
        }

        sale = SaleService.complete_sale(
            items_data=items_data,
            payment_data=payment_data,
            cashier=self.user,
            customer_data=customer_data,
        )

        # Assert Sale record properties
        self.assertEqual(sale.contact, self.contact)
        self.assertEqual(sale.order_channel, OrderChannel.WHATSAPP)
        self.assertEqual(sale.grand_total, Decimal('3700.00'))
        self.assertTrue(sale.is_online)

        # Assert Steadfast courier details populated
        self.assertTrue(bool(sale.courier_tracking_code))
        self.assertTrue(bool(sale.courier_consignment_id))
        self.assertIn('steadfast.com.bd/t/', sale.tracking_url)

        # Assert inventory deducted
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 48)

        # Assert automated message was sent
        conv = Conversation.objects.filter(contact=self.contact).first()
        self.assertIsNotNone(conv)
        self.assertTrue(conv.messages.filter(direction=Message.Direction.OUTBOUND).exists())

    def test_auto_messaging_template_render(self):
        """Test variable substitution in automated messages."""
        tpl = "Hello {customer_name}! Order {invoice_number} total {currency_symbol} {grand_total}."
        ctx = {
            'customer_name': 'Rahim',
            'invoice_number': 'INV-999',
            'currency_symbol': '৳',
            'grand_total': '2,500.00'
        }
        rendered = AutoMessagingService.render(tpl, ctx)
        self.assertEqual(rendered, "Hello Rahim! Order INV-999 total ৳ 2,500.00.")

    def test_inbound_tracking_bot(self):
        """Test customer inbound message auto-reply for order tracking."""
        # Create an existing sale for the contact
        items_data = [{
            'product_id': self.product.id,
            'quantity': 1,
            'unit_price': self.product.current_price,
            'discount': Decimal('0.00'),
        }]
        sale = SaleService.complete_sale(
            items_data=items_data,
            payment_data={'payment_method': 'CASH', 'amount_paid': Decimal('0.00')},
            cashier=self.user,
            customer_data={'contact_id': self.contact.id, 'order_channel': 'WHATSAPP', 'delivery_address': 'Banani'},
        )

        conv, _ = Conversation.objects.get_or_create(
            contact=self.contact,
            platform=Platform.WHATSAPP,
            defaults={'platform_thread_id': 'bot-test'}
        )

        # Simulate customer asking for order tracking
        reply = AutoMessagingService.process_inbound_bot(conv, "Where is my order? Please track")
        self.assertIsNotNone(reply)
        self.assertIn(sale.invoice_number, reply.body)
        self.assertIn("Steadfast", reply.body)
