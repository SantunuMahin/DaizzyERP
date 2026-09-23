"""
Automated Messaging and Notification Rules Engine.
Provides event-driven dispatch (Order Confirmation, Steadfast Courier Dispatch, Delivery)
and Inbound Customer Order Tracking Bot.
"""
import logging
import re
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from apps.messaging.models import Contact, Conversation, Message, Platform

logger = logging.getLogger(__name__)


# Default message templates with dynamic placeholders
DEFAULT_TEMPLATES = {
    'ORDER_CONFIRMED': (
        "Hello {customer_name}! 🎉\n\n"
        "Thank you for ordering with {store_name}!\n"
        "Your order #{invoice_number} is confirmed.\n\n"
        "📦 Items: {items_summary}\n"
        "💰 Total: {currency_symbol} {grand_total}\n"
        "💵 Payment: {payment_status}\n"
        "📍 Delivery Address: {delivery_address}\n\n"
        "We are preparing your package. You will receive courier tracking details once dispatched! 🚚"
    ),
    'COURIER_DISPATCHED': (
        "Great news, {customer_name}! 🚀\n\n"
        "Your order #{invoice_number} has been dispatched via {courier_service}!\n\n"
        "📦 Consignment ID: {consignment_id}\n"
        "🏷️ Tracking Code: {tracking_code}\n"
        "💵 COD to Pay: {currency_symbol} {cod_amount}\n"
        "🔗 Live Tracking: {tracking_url}\n\n"
        "The courier will contact you at {customer_phone} prior to delivery. Thank you for choosing us!"
    ),
    'ORDER_DELIVERED': (
        "Dear {customer_name} 🌸\n\n"
        "Your order #{invoice_number} has been delivered successfully!\n"
        "We hope you love your purchase. If you have any feedback or questions, feel free to reply right here."
    ),
    'ORDER_CANCELLED': (
        "Dear {customer_name},\n\n"
        "Your order #{invoice_number} has been cancelled. If this was unexpected, please reach out to us."
    ),
    'TRACKING_BOT_REPLY': (
        "Hi {customer_name}! Here is your latest order status:\n\n"
        "🧾 Invoice: #{invoice_number}\n"
        "📅 Date: {order_date}\n"
        "📦 Status: {order_status}\n"
        "🚚 Courier: {courier_service} ({courier_status})\n"
        "🏷️ Tracking: {tracking_code}\n"
        "🔗 Live Track: {tracking_url}\n"
        "💰 Total: {currency_symbol} {grand_total} ({payment_status})\n\n"
        "Let us know if you need any further assistance!"
    ),
}


class AutoMessagingService:
    """Orchestrates automated notifications and customer inquiries."""

    @classmethod
    def get_template(cls, event_type: str) -> str:
        """Fetch custom template or default."""
        try:
            from apps.messaging.models import MessageTemplate
            tpl = MessageTemplate.objects.filter(category=f"auto_{event_type.lower()}", is_active=True).first()
            if tpl and tpl.body.strip():
                return tpl.body
        except Exception:
            pass
        return DEFAULT_TEMPLATES.get(event_type, "")

    @classmethod
    def get_or_create_conversation(cls, contact: Contact, preferred_platform: str = None) -> Conversation:
        """Find best active conversation or create one on contact's primary channel."""
        # Check active conversations
        conv = contact.conversations.filter(status=Conversation.Status.OPEN).first()
        if conv:
            return conv

        # Find preferred platform
        platform = preferred_platform
        if not platform:
            if contact.whatsapp_number:
                platform = Platform.WHATSAPP
            elif contact.messenger_id:
                platform = Platform.MESSENGER
            elif contact.telegram_id or contact.telegram_username:
                platform = Platform.TELEGRAM
            elif contact.email:
                platform = Platform.EMAIL
            else:
                platform = Platform.INTERNAL

        conv, _ = Conversation.objects.get_or_create(
            contact=contact,
            platform=platform,
            defaults={'platform_thread_id': f"auto-{contact.id}-{platform}"}
        )
        return conv

    @classmethod
    def build_sale_context(cls, sale) -> dict:
        """Extract clean template variables from a Sale instance."""
        items = list(sale.items.all()[:4])
        items_summary = ", ".join(f"{it.product_name} (x{it.quantity})" for it in items)
        if sale.items.count() > 4:
            items_summary += f" +{sale.items.count() - 4} more"

        due = max(Decimal('0.00'), sale.grand_total - sale.amount_paid)

        store_name = getattr(settings, 'STORE_NAME', 'Daizzy')
        currency_symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '৳')

        return {
            'customer_name': sale.customer_name or 'Valued Customer',
            'customer_phone': sale.customer_phone or '',
            'store_name': store_name,
            'currency_symbol': currency_symbol,
            'invoice_number': sale.invoice_number,
            'grand_total': f"{sale.grand_total:,.2f}",
            'amount_paid': f"{sale.amount_paid:,.2f}",
            'cod_amount': f"{due:,.2f}",
            'payment_status': sale.get_payment_status_display() if hasattr(sale, 'get_payment_status_display') else sale.payment_status,
            'order_status': sale.get_status_display() if hasattr(sale, 'get_status_display') else sale.status,
            'items_summary': items_summary or 'Items in Order',
            'delivery_address': sale.delivery_address or 'Standard Delivery Address',
            'courier_service': (sale.courier_service or 'Steadfast Courier').title(),
            'consignment_id': sale.courier_consignment_id or 'Pending',
            'tracking_code': sale.courier_tracking_code or 'Pending',
            'courier_status': sale.get_courier_status_display() if hasattr(sale, 'get_courier_status_display') else (sale.courier_status or 'Processing'),
            'tracking_url': sale.tracking_url or 'https://steadfast.com.bd',
            'order_date': sale.created_at.strftime("%d %b %Y, %I:%M %p") if sale.created_at else '',
        }

    @classmethod
    def render(cls, template_str: str, context: dict) -> str:
        """Safely substitute {key} variables in text."""
        result = template_str
        for k, v in context.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

    @classmethod
    def dispatch_auto_message(cls, contact: Contact, body: str, preferred_platform: str = None) -> Message or None:
        """Route message through unified dispatcher."""
        if not contact or not body:
            return None

        conv = cls.get_or_create_conversation(contact, preferred_platform)
        from apps.messaging.services.dispatcher import send_message
        try:
            msg = send_message(conv, body, sent_by=None)
            logger.info(f"Auto-message dispatched to Contact {contact.name} ({conv.platform}): {body[:40]}...")
            return msg
        except Exception as e:
            logger.error(f"Failed to dispatch auto-message to {contact.name}: {e}")
            return None

    @classmethod
    def on_order_confirmed(cls, sale) -> Message or None:
        """Triggered when an order is created or confirmed."""
        contact = sale.contact
        if not contact and sale.customer_phone:
            # Auto-find or create contact
            contact = Contact.objects.filter(phone=sale.customer_phone).first() or \
                      Contact.objects.filter(whatsapp_number=sale.customer_phone).first()
            if not contact and sale.customer_name:
                contact = Contact.objects.create(
                    name=sale.customer_name,
                    phone=sale.customer_phone,
                    whatsapp_number=sale.customer_phone,
                    email=sale.customer_email or '',
                )
            if contact:
                sale.contact = contact
                sale.save(update_fields=['contact'])

        if not contact:
            logger.info(f"Skipping auto-message for order {sale.invoice_number}: No contact linked.")
            return None

        tpl = cls.get_template('ORDER_CONFIRMED')
        ctx = cls.build_sale_context(sale)
        body = cls.render(tpl, ctx)

        platform = None
        if sale.order_channel == 'WHATSAPP': platform = Platform.WHATSAPP
        elif sale.order_channel == 'MESSENGER': platform = Platform.MESSENGER
        elif sale.order_channel == 'TELEGRAM': platform = Platform.TELEGRAM

        return cls.dispatch_auto_message(contact, body, preferred_platform=platform)

    @classmethod
    def on_courier_dispatched(cls, sale) -> Message or None:
        """Triggered when Steadfast Courier booking is confirmed."""
        contact = sale.contact
        if not contact:
            return None

        tpl = cls.get_template('COURIER_DISPATCHED')
        ctx = cls.build_sale_context(sale)
        body = cls.render(tpl, ctx)

        return cls.dispatch_auto_message(contact, body)

    @classmethod
    def on_order_delivered(cls, sale) -> Message or None:
        """Triggered when Steadfast / Cashier marks order delivered."""
        contact = sale.contact
        if not contact:
            return None

        tpl = cls.get_template('ORDER_DELIVERED')
        ctx = cls.build_sale_context(sale)
        body = cls.render(tpl, ctx)

        return cls.dispatch_auto_message(contact, body)

    @classmethod
    def process_inbound_bot(cls, conversation: Conversation, inbound_body: str) -> Message or None:
        """
        Intelligent Inbound Customer Bot.
        Detects if customer asks for order status, tracking, or mentions an invoice.
        """
        body_lower = (inbound_body or '').strip().lower()
        contact = conversation.contact

        # Check for keywords or invoice patterns
        trigger_keywords = ['track', 'status', 'order', 'parcel', 'courier', 'delivery', 'কোথায়', 'অর্ডার', 'ট্র্যাক', 'ডেলিভারি']
        is_tracking_intent = any(kw in body_lower for kw in trigger_keywords)

        # Check if text contains an invoice pattern like INV-2026...
        invoice_match = re.search(r'(INV-[A-Z0-9\-]+)', inbound_body, re.IGNORECASE)

        target_sale = None
        if invoice_match:
            inv_no = invoice_match.group(1).upper()
            from apps.sales.models import Sale
            target_sale = Sale.objects.filter(invoice_number__iexact=inv_no).first()

        if not target_sale and is_tracking_intent:
            from apps.sales.models import Sale
            # Find contact's most recent sale
            target_sale = Sale.objects.filter(contact=contact).order_by('-created_at').first()
            if not target_sale and contact.phone:
                target_sale = Sale.objects.filter(customer_phone=contact.phone).order_by('-created_at').first()

        if target_sale:
            tpl = cls.get_template('TRACKING_BOT_REPLY')
            ctx = cls.build_sale_context(target_sale)
            reply_text = cls.render(tpl, ctx)

            from apps.messaging.services.dispatcher import send_message
            return send_message(conversation, reply_text, sent_by=None)

        return None
