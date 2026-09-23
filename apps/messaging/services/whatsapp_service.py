"""
WhatsApp Business Cloud API Service
Handles sending and receiving WhatsApp messages via Meta's Graph API.
"""
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = 'v19.0'
GRAPH_API_BASE = f'https://graph.facebook.com/{GRAPH_API_VERSION}'


def _get_config():
    """Lazy-load platform config to avoid circular imports."""
    from apps.messaging.models import PlatformConfig, Platform
    try:
        return PlatformConfig.objects.get(platform=Platform.WHATSAPP, is_active=True)
    except PlatformConfig.DoesNotExist:
        return None


def send_text_message(to_phone: str, body: str) -> dict:
    """
    Send a plain text WhatsApp message.
    Args:
        to_phone: Recipient's E.164 formatted phone number (e.g. +8801XXXXXXXXX)
        body:     The message text
    Returns:
        API response dict or error dict
    """
    config = _get_config()
    if not config:
        return {'error': 'WhatsApp not configured or inactive.'}

    url = f'{GRAPH_API_BASE}/{config.phone_number_id}/messages'
    headers = {
        'Authorization': f'Bearer {config.access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to_phone.replace('+', '').replace(' ', ''),
        'type': 'text',
        'text': {'preview_url': False, 'body': body},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'WhatsApp send_text_message failed: {e}')
        return {'error': str(e)}


def send_template_message(to_phone: str, template_name: str,
                          language_code: str = 'en_US',
                          components: Optional[list] = None) -> dict:
    """
    Send a WhatsApp approved template message.
    """
    config = _get_config()
    if not config:
        return {'error': 'WhatsApp not configured or inactive.'}

    url = f'{GRAPH_API_BASE}/{config.phone_number_id}/messages'
    headers = {
        'Authorization': f'Bearer {config.access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_phone.replace('+', '').replace(' ', ''),
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language_code},
            'components': components or [],
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'WhatsApp send_template_message failed: {e}')
        return {'error': str(e)}


def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    """Verify Meta webhook challenge."""
    config = _get_config()
    if not config:
        return None
    if mode == 'subscribe' and token == config.webhook_verify_token:
        return challenge
    return None


def parse_webhook_payload(payload: dict) -> list:
    """
    Parse an inbound WhatsApp webhook payload into a list of message dicts.
    Returns:
        List of {'from_phone', 'wa_message_id', 'message_type', 'body', 'timestamp'}
    """
    messages = []
    try:
        entries = payload.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for msg in value.get('messages', []):
                    msg_type = msg.get('type', 'text')
                    body = ''
                    if msg_type == 'text':
                        body = msg.get('text', {}).get('body', '')
                    elif msg_type == 'image':
                        body = '[Image]'
                    elif msg_type == 'document':
                        body = '[Document]'
                    elif msg_type == 'audio':
                        body = '[Audio]'

                    messages.append({
                        'from_phone': msg.get('from', ''),
                        'wa_message_id': msg.get('id', ''),
                        'message_type': msg_type,
                        'body': body,
                        'timestamp': msg.get('timestamp', ''),
                    })
    except (KeyError, TypeError) as e:
        logger.error(f'WhatsApp parse_webhook_payload error: {e}')
    return messages
