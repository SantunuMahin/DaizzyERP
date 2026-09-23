"""
Messaging Hub — Data Models
Provides Contact CRM, Conversations, Messages, Platform Config, and Templates.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM CHOICES
# ─────────────────────────────────────────────────────────────────────────────
class Platform(models.TextChoices):
    WHATSAPP  = 'whatsapp',  'WhatsApp'
    MESSENGER = 'messenger', 'Facebook Messenger'
    INSTAGRAM = 'instagram', 'Instagram DM'
    TELEGRAM  = 'telegram',  'Telegram'
    EMAIL     = 'email',     'Email'
    INTERNAL  = 'internal',  'Internal Note'


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM CONFIGURATION — API keys & credentials per platform
# ─────────────────────────────────────────────────────────────────────────────
class PlatformConfig(models.Model):
    """Stores credentials and settings for each messaging platform."""
    platform = models.CharField(
        max_length=30, choices=Platform.choices, unique=True,
        verbose_name='Platform'
    )
    is_active = models.BooleanField(default=False, verbose_name='Active')
    display_name = models.CharField(max_length=100, blank=True)

    # WhatsApp Business / Meta Graph API
    access_token = models.TextField(blank=True, verbose_name='Access Token / API Key')
    phone_number_id = models.CharField(max_length=100, blank=True, verbose_name='Phone Number ID')
    business_account_id = models.CharField(max_length=100, blank=True, verbose_name='Business Account ID')
    app_id = models.CharField(max_length=100, blank=True, verbose_name='App ID')

    # Webhook verification
    webhook_verify_token = models.CharField(max_length=255, blank=True, verbose_name='Webhook Verify Token')

    # Telegram
    bot_token = models.CharField(max_length=255, blank=True, verbose_name='Bot Token')
    bot_username = models.CharField(max_length=100, blank=True, verbose_name='Bot Username')

    # Email (SMTP/IMAP)
    smtp_host = models.CharField(max_length=255, blank=True, default='smtp.gmail.com')
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.EmailField(blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.PositiveIntegerField(default=993)

    # Meta
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        verbose_name = 'Platform Configuration'
        verbose_name_plural = 'Platform Configurations'

    def __str__(self):
        return f"{self.get_platform_display()} — {'Active' if self.is_active else 'Inactive'}"

    @property
    def icon(self):
        icons = {
            'whatsapp': '💬', 'messenger': '💙',
            'instagram': '📸', 'telegram': '✈️', 'email': '📧',
        }
        return icons.get(self.platform, '💬')

    @property
    def color_class(self):
        return {
            'whatsapp': 'wab', 'messenger': 'msn',
            'instagram': 'ins', 'telegram': 'tlg', 'email': 'eml',
        }.get(self.platform, '')


# ─────────────────────────────────────────────────────────────────────────────
# CONTACT — CRM contact record
# ─────────────────────────────────────────────────────────────────────────────
class Contact(models.Model):
    """CRM contact linked to conversations and optionally to sales orders."""
    name = models.CharField(max_length=200, verbose_name='Full Name')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Phone / WhatsApp')
    email = models.EmailField(blank=True, verbose_name='Email')
    company = models.CharField(max_length=200, blank=True, verbose_name='Company')
    avatar_color = models.CharField(max_length=7, default='#7C3AED')  # hex for fallback avatar
    notes = models.TextField(blank=True, verbose_name='Notes')
    tags = models.CharField(max_length=500, blank=True, verbose_name='Tags (comma-separated)')

    # Social handles
    whatsapp_number = models.CharField(max_length=30, blank=True)
    messenger_id = models.CharField(max_length=100, blank=True)
    instagram_id = models.CharField(max_length=100, blank=True)
    telegram_id = models.CharField(max_length=100, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)

    # Lifecycle
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_contacts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def total_messages(self):
        return Message.objects.filter(conversation__contact=self).count()

    @property
    def last_message(self):
        return Message.objects.filter(
            conversation__contact=self
        ).order_by('-created_at').first()

    @property
    def available_platforms(self):
        platforms = []
        if self.whatsapp_number: platforms.append('whatsapp')
        if self.messenger_id: platforms.append('messenger')
        if self.instagram_id: platforms.append('instagram')
        if self.telegram_id or self.telegram_username: platforms.append('telegram')
        if self.email: platforms.append('email')
        return platforms


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION — A thread between a contact and the business on one platform
# ─────────────────────────────────────────────────────────────────────────────
class Conversation(models.Model):
    class Status(models.TextChoices):
        OPEN     = 'open',     'Open'
        RESOLVED = 'resolved', 'Resolved'
        PENDING  = 'pending',  'Pending'
        SPAM     = 'spam',     'Spam'

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='conversations'
    )
    platform = models.CharField(
        max_length=30, choices=Platform.choices, default=Platform.WHATSAPP
    )
    platform_thread_id = models.CharField(
        max_length=255, blank=True,
        help_text='External thread/chat ID on the platform'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    subject = models.CharField(max_length=255, blank=True)  # useful for email
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='assigned_conversations'
    )
    unread_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'

    def __str__(self):
        return f"{self.contact.name} via {self.get_platform_display()} ({self.status})"

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def mark_read(self):
        self.unread_count = 0
        self.save(update_fields=['unread_count'])
        self.messages.filter(direction='inbound', is_read=False).update(is_read=True)


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE — A single message in a conversation
# ─────────────────────────────────────────────────────────────────────────────
class Message(models.Model):
    class Direction(models.TextChoices):
        INBOUND  = 'inbound',  'Inbound (Received)'
        OUTBOUND = 'outbound', 'Outbound (Sent)'

    class MessageType(models.TextChoices):
        TEXT     = 'text',     'Text'
        IMAGE    = 'image',    'Image'
        DOCUMENT = 'document', 'Document'
        AUDIO    = 'audio',    'Audio'
        VIDEO    = 'video',    'Video'
        TEMPLATE = 'template', 'Template'
        NOTE     = 'note',     'Internal Note'

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    direction = models.CharField(
        max_length=10, choices=Direction.choices, default=Direction.INBOUND
    )
    message_type = models.CharField(
        max_length=15, choices=MessageType.choices, default=MessageType.TEXT
    )
    body = models.TextField(blank=True, verbose_name='Message Body')
    media_url = models.URLField(blank=True, verbose_name='Media URL')
    media_mime = models.CharField(max_length=100, blank=True)

    # Platform metadata
    platform_message_id = models.CharField(max_length=255, blank=True, unique=False)
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)

    # Sender (for outbound)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sent_messages'
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"[{self.direction}] {self.body[:60]}"

    @property
    def is_outbound(self):
        return self.direction == self.Direction.OUTBOUND

    @property
    def sender_name(self):
        if self.sent_by:
            return self.sent_by.get_full_name() or self.sent_by.username
        return "Daizzy System"


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE TEMPLATE — Reusable message templates for bulk/quick replies
# ─────────────────────────────────────────────────────────────────────────────
class MessageTemplate(models.Model):
    name = models.CharField(max_length=100)
    platform = models.CharField(
        max_length=30, choices=Platform.choices, blank=True,
        help_text='Leave blank to apply to all platforms'
    )
    category = models.CharField(max_length=50, blank=True,
                                help_text='e.g. greeting, follow-up, promotion')
    body = models.TextField()
    variables = models.JSONField(
        default=list, blank=True,
        help_text='List of variable names like ["name", "order_id"]'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'

    def __str__(self):
        return self.name

    def render(self, context: dict) -> str:
        """Replace {{variable}} placeholders with context values."""
        text = self.body
        for key, val in context.items():
            text = text.replace(f'{{{{{key}}}}}', str(val))
        return text
