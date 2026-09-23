"""
Message Dispatcher — Unified send interface for all platforms.
Routes outbound messages to the correct platform service.
"""
import logging
from django.utils import timezone
from apps.messaging.models import Conversation, Message, Platform

logger = logging.getLogger(__name__)


def send_message(conversation: Conversation, body: str, sent_by=None) -> Message:
    """
    Send a message on the conversation's platform and record it in DB.
    Args:
        conversation: The Conversation to send on.
        body:         Message text.
        sent_by:      User who sent the message (or None for system).
    Returns:
        The saved Message instance.
    """
    platform = conversation.platform
    contact = conversation.contact
    result = {}

    # ── Route to correct platform service ─────────────────────────────────
    if platform == Platform.WHATSAPP:
        from apps.messaging.services import whatsapp_service
        phone = contact.whatsapp_number or contact.phone
        if phone:
            result = whatsapp_service.send_text_message(phone, body)
        else:
            result = {'error': 'No WhatsApp number for contact.'}

    elif platform == Platform.MESSENGER:
        from apps.messaging.services import messenger_service
        if contact.messenger_id:
            result = messenger_service.send_text_message(contact.messenger_id, body)
        else:
            result = {'error': 'No Messenger PSID for contact.'}

    elif platform == Platform.TELEGRAM:
        from apps.messaging.services import telegram_service
        chat_id = contact.telegram_id or contact.telegram_username
        if chat_id:
            result = telegram_service.send_text_message(chat_id, body)
        else:
            result = {'error': 'No Telegram ID for contact.'}

    elif platform == Platform.EMAIL:
        from apps.messaging.services import email_service
        if contact.email:
            result = email_service.send_email(
                contact.email,
                subject=conversation.subject or 'Message from Daizzy',
                body=body
            )
        else:
            result = {'error': 'No email for contact.'}

    elif platform == Platform.INTERNAL:
        result = {'success': True}

    else:
        result = {'error': f'Unknown platform: {platform}'}

    if 'error' in result:
        logger.warning(f'Message dispatch error: {result["error"]}')

    # ── Save message record ────────────────────────────────────────────────
    msg = Message.objects.create(
        conversation=conversation,
        direction=Message.Direction.OUTBOUND,
        body=body,
        sent_by=sent_by,
        is_delivered='error' not in result,
        platform_message_id=result.get('messages', [{}])[0].get('id', '') if 'messages' in result else '',
    )

    # Update conversation timestamp
    conversation.save(update_fields=['updated_at'])
    return msg


def ingest_inbound(platform: str, platform_thread_id: str,
                   sender_identifier: str, sender_name: str,
                   body: str, platform_message_id: str = '') -> Message:
    """
    Process an inbound message from a webhook and create/update Contact + Conversation + Message.
    Args:
        platform:             Platform string (e.g. 'whatsapp')
        platform_thread_id:   External chat/thread ID
        sender_identifier:    Phone number, PSID, or Telegram ID
        sender_name:          Name from the platform (best-effort)
        body:                 Message text
        platform_message_id:  External message ID for deduplication
    Returns:
        The saved inbound Message instance.
    """
    from apps.messaging.models import Contact

    # Dedup: skip if we already have this platform message
    if platform_message_id:
        existing = Message.objects.filter(platform_message_id=platform_message_id).first()
        if existing:
            return existing

    # Find or create contact
    contact = None
    if platform == Platform.WHATSAPP:
        contact = Contact.objects.filter(whatsapp_number=sender_identifier).first()
        if not contact and sender_identifier:
            contact = Contact.objects.filter(phone=sender_identifier).first()
        if not contact:
            contact = Contact.objects.create(
                name=sender_name or sender_identifier,
                phone=sender_identifier,
                whatsapp_number=sender_identifier,
            )
    elif platform == Platform.MESSENGER:
        contact = Contact.objects.filter(messenger_id=sender_identifier).first()
        if not contact:
            contact = Contact.objects.create(
                name=sender_name or f'Messenger User {sender_identifier[:8]}',
                messenger_id=sender_identifier,
            )
    elif platform == Platform.TELEGRAM:
        contact = Contact.objects.filter(telegram_id=sender_identifier).first()
        if not contact:
            contact = Contact.objects.create(
                name=sender_name or f'Telegram User {sender_identifier}',
                telegram_id=sender_identifier,
            )

    if not contact:
        contact = Contact.objects.create(name=sender_name or sender_identifier)

    # Find or create conversation
    conv = Conversation.objects.filter(
        contact=contact,
        platform=platform,
        platform_thread_id=platform_thread_id,
    ).first()

    if not conv:
        conv = Conversation.objects.create(
            contact=contact,
            platform=platform,
            platform_thread_id=platform_thread_id,
            status=Conversation.Status.OPEN,
        )

    # Increment unread count
    conv.unread_count = (conv.unread_count or 0) + 1
    conv.save(update_fields=['unread_count', 'updated_at'])

    # Save message
    msg = Message.objects.create(
        conversation=conv,
        direction=Message.Direction.INBOUND,
        body=body,
        platform_message_id=platform_message_id,
        is_read=False,
    )

    # Trigger intelligent tracking auto-reply bot if requested by customer
    try:
        from apps.messaging.services.auto_messaging import AutoMessagingService
        AutoMessagingService.process_inbound_bot(conv, body)
    except Exception as e:
        logger.warning(f"Error processing inbound auto-reply bot: {e}")

    return msg
