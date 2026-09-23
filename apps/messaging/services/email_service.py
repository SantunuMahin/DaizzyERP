"""
Email Service
Sends outbound emails via SMTP using the configured PlatformConfig credentials.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_config():
    from apps.messaging.models import PlatformConfig, Platform
    try:
        return PlatformConfig.objects.get(platform=Platform.EMAIL, is_active=True)
    except PlatformConfig.DoesNotExist:
        return None


def send_email(to_address: str, subject: str, body: str, html_body: str = '') -> dict:
    """
    Send an email using the configured SMTP settings.
    Args:
        to_address: Recipient email address.
        subject:    Email subject.
        body:       Plain text body.
        html_body:  Optional HTML body (used if provided).
    """
    config = _get_config()
    if not config:
        return {'error': 'Email not configured or inactive.'}

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config.smtp_username
    msg['To'] = to_address

    msg.attach(MIMEText(body, 'plain'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))

    try:
        if config.smtp_use_tls:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=20)

        server.login(config.smtp_username, config.smtp_password)
        server.sendmail(config.smtp_username, to_address, msg.as_string())
        server.quit()
        return {'success': True, 'to': to_address}
    except Exception as e:
        logger.error(f'Email send_email failed: {e}')
        return {'error': str(e)}


def send_invoice_email(to_address: str, contact_name: str,
                       invoice_number: str, amount: str, currency: str = '৳') -> dict:
    """Convenience: send a pre-formatted invoice notification email."""
    subject = f'Invoice #{invoice_number} from Daizzy'
    plain = (
        f'Dear {contact_name},\n\n'
        f'Your invoice #{invoice_number} for {currency}{amount} is ready.\n\n'
        f'Thank you for your business!\n\nDaizzy Team'
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg, #7C3AED, #06B6D4); padding: 32px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">D</h1>
        <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0; font-size: 13px;">Daizzy ERP</p>
      </div>
      <div style="background: #F8FAFC; padding: 32px; border-radius: 0 0 12px 12px;">
        <h2 style="color: #0F172A;">Invoice #{invoice_number}</h2>
        <p style="color: #64748B;">Dear <strong>{contact_name}</strong>,</p>
        <p style="color: #64748B;">Your invoice is ready for payment.</p>
        <div style="background: #7C3AED; color: white; border-radius: 8px; padding: 16px 24px; display: inline-block; font-size: 24px; font-weight: bold; margin: 16px 0;">
          {currency}{amount}
        </div>
        <p style="color: #94A3B8; font-size: 13px; margin-top: 24px;">Thank you for your business.<br>Daizzy Team</p>
      </div>
    </div>
    """
    return send_email(to_address, subject, plain, html)
