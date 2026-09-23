"""
Messaging Hub — URL Configuration
"""
from django.urls import path
from . import views, views_order, views_rules

app_name = 'messaging'

urlpatterns = [
    # ── Inbox & conversations ──────────────────────────────────────────────
    path('inbox/', views.InboxView.as_view(), name='inbox'),
    path('inbox/send/', views.SendMessageView.as_view(), name='send_message'),
    path('inbox/send/<int:conv_id>/', views.SendMessageView.as_view(), name='send_message_conv'),
    path('inbox/new/', views.NewConversationView.as_view(), name='new_conversation'),

    # ── Contacts CRM ──────────────────────────────────────────────────────
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('contacts/new/', views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/<int:pk>/edit/', views.ContactCreateView.as_view(), name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),

    # ── Platform settings ──────────────────────────────────────────────────
    path('platforms/', views.PlatformConfigView.as_view(), name='platform_config'),

    # ── Webhooks (no auth, CSRF-exempt) ───────────────────────────────────
    path('webhooks/whatsapp/', views.WhatsAppWebhookView.as_view(), name='webhook_whatsapp'),
    path('webhooks/messenger/', views.MessengerWebhookView.as_view(), name='webhook_messenger'),
    path('webhooks/telegram/', views.TelegramWebhookView.as_view(), name='webhook_telegram'),

    # ── Polling API ────────────────────────────────────────────────────────
    path('api/messages/<int:conv_id>/', views.ConversationMessagesAPIView.as_view(), name='api_messages'),
    path('api/unread/', views.UnreadCountAPIView.as_view(), name='api_unread'),

    # ── Messaging-to-Order Connection & CRM Bridge ──────────────────────────
    path('orders/quick-create/', views_order.QuickOrderCreateView.as_view(), name='quick_order_create'),
    path('api/contacts/<int:contact_id>/orders/', views_order.ContactOrdersAPIView.as_view(), name='api_contact_orders'),

    # ── Automated Messaging Rules ──────────────────────────────────────────
    path('auto-rules/', views_rules.AutoMessagingRulesView.as_view(), name='auto_rules'),
]
