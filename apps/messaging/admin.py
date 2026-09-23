from django.contrib import admin
from .models import Contact, Conversation, Message, PlatformConfig, MessageTemplate


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ['platform', 'is_active', 'updated_at']
    list_filter = ['platform', 'is_active']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'company', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'phone', 'email', 'company']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['contact', 'platform', 'status', 'unread_count', 'updated_at']
    list_filter = ['platform', 'status']
    search_fields = ['contact__name']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'direction', 'message_type', 'body', 'created_at']
    list_filter = ['direction', 'message_type', 'is_read']
    search_fields = ['body', 'conversation__contact__name']


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'category', 'is_active']
    list_filter = ['platform', 'is_active']
