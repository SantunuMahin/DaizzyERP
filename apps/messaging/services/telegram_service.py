"""
Telegram Bot API Service
Sends messages using Telegram Bot API (https://core.telegram.org/bots/api).
"""
import logging
import requests

logger = logging.getLogger(__name__)
TELEGRAM_API_BASE = 'https://api.telegram.org/bot'


def _get_config():
    from apps.messaging.models import PlatformConfig, Platform
    try:
        return PlatformConfig.objects.get(platform=Platform.TELEGRAM, is_active=True)
    except PlatformConfig.DoesNotExist:
        return None


def send_text_message(chat_id: str, body: str, parse_mode: str = 'HTML') -> dict:
    """
    Send a text message to a Telegram chat (user or group).
    Args:
        chat_id: Telegram chat ID or username (@username).
        body: Message text (supports HTML or Markdown).
        parse_mode: 'HTML' or 'Markdown'.
    """
    config = _get_config()
    if not config:
        return {'error': 'Telegram not configured or inactive.'}

    url = f'{TELEGRAM_API_BASE}{config.bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': body,
        'parse_mode': parse_mode,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'Telegram send_text_message failed: {e}')
        return {'error': str(e)}


def set_webhook(webhook_url: str) -> dict:
    """Register a webhook URL with Telegram to receive updates."""
    config = _get_config()
    if not config:
        return {'error': 'Telegram not configured.'}
    url = f'{TELEGRAM_API_BASE}{config.bot_token}/setWebhook'
    try:
        response = requests.post(url, json={'url': webhook_url}, timeout=15)
        return response.json()
    except requests.RequestException as e:
        return {'error': str(e)}


def parse_webhook_payload(payload: dict) -> list:
    """Parse a Telegram Update object into message dicts."""
    messages = []
    try:
        message = payload.get('message') or payload.get('edited_message')
        if message:
            chat = message.get('chat', {})
            from_user = message.get('from', {})
            messages.append({
                'chat_id': str(chat.get('id', '')),
                'username': from_user.get('username', ''),
                'first_name': from_user.get('first_name', ''),
                'message_id': message.get('message_id', ''),
                'body': message.get('text', '[Non-text message]'),
            })
    except (KeyError, TypeError) as e:
        logger.error(f'Telegram parse_webhook_payload error: {e}')
    return messages
