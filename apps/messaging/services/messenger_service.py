"""
Facebook Messenger API Service
Sends messages via the Meta Graph API Send API.
"""
import logging
import requests

logger = logging.getLogger(__name__)
GRAPH_API_VERSION = 'v19.0'
GRAPH_BASE = f'https://graph.facebook.com/{GRAPH_API_VERSION}'


def _get_config():
    from apps.messaging.models import PlatformConfig, Platform
    try:
        return PlatformConfig.objects.get(platform=Platform.MESSENGER, is_active=True)
    except PlatformConfig.DoesNotExist:
        return None


def send_text_message(recipient_psid: str, body: str) -> dict:
    """
    Send a text message to a Facebook Messenger user.
    Args:
        recipient_psid: The Page-Scoped User ID of the recipient.
        body: Message text.
    """
    config = _get_config()
    if not config:
        return {'error': 'Messenger not configured or inactive.'}

    url = f'{GRAPH_BASE}/me/messages'
    params = {'access_token': config.access_token}
    payload = {
        'recipient': {'id': recipient_psid},
        'message': {'text': body},
        'messaging_type': 'RESPONSE',
    }

    try:
        response = requests.post(url, params=params, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'Messenger send_text_message failed: {e}')
        return {'error': str(e)}


def parse_webhook_payload(payload: dict) -> list:
    """Parse inbound Messenger webhook into message dicts."""
    messages = []
    try:
        for entry in payload.get('entry', []):
            for messaging in entry.get('messaging', []):
                sender_id = messaging.get('sender', {}).get('id', '')
                msg = messaging.get('message', {})
                if msg:
                    messages.append({
                        'sender_id': sender_id,
                        'mid': msg.get('mid', ''),
                        'body': msg.get('text', '[Non-text message]'),
                    })
    except (KeyError, TypeError) as e:
        logger.error(f'Messenger parse_webhook_payload error: {e}')
    return messages
