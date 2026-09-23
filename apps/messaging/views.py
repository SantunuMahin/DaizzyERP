"""
Messaging Hub — Views
Unified inbox, contacts CRM, webhooks, and platform configuration.
"""
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages as flash_messages
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Contact, Conversation, Message, PlatformConfig, Platform, MessageTemplate

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# INBOX — Unified conversation list + chat panel
# ─────────────────────────────────────────────────────────────────────────────
class InboxView(LoginRequiredMixin, TemplateView):
    template_name = 'messaging/inbox.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        platform_filter = self.request.GET.get('platform', '')
        status_filter = self.request.GET.get('status', 'open')
        search = self.request.GET.get('q', '').strip()
        filter_type = self.request.GET.get('filter', 'all')  # all|unread|mentions
        conv_id = self.request.GET.get('conv')

        conversations = Conversation.objects.select_related('contact').order_by('-updated_at')

        if platform_filter:
            conversations = conversations.filter(platform=platform_filter)
        if status_filter:
            conversations = conversations.filter(status=status_filter)
        if filter_type == 'unread':
            conversations = conversations.filter(unread_count__gt=0)
        if search:
            conversations = conversations.filter(
                Q(contact__name__icontains=search) |
                Q(contact__phone__icontains=search) |
                Q(messages__body__icontains=search)
            ).distinct()

        # Active conversation
        active_conv = None
        chat_messages = []
        if conv_id:
            try:
                active_conv = Conversation.objects.select_related('contact', 'assigned_to').get(
                    pk=conv_id
                )
                active_conv.mark_read()
                chat_messages = active_conv.messages.order_by('created_at')
            except Conversation.DoesNotExist:
                pass
        elif conversations.exists():
            active_conv = conversations.first()
            if active_conv:
                active_conv.mark_read()
                chat_messages = active_conv.messages.order_by('created_at')

        # Platform stats for tabs
        platform_counts = {}
        for p in Platform.values:
            platform_counts[p] = Conversation.objects.filter(
                platform=p, status='open'
            ).count()

        total_unread = Conversation.objects.filter(unread_count__gt=0).aggregate(
            total=Count('id')
        )['total'] or 0

        # Active contact order history & products for in-chat quick ordering
        contact_orders = []
        contact_total_spent = 0
        contact_order_count = 0
        if active_conv and active_conv.contact:
            from apps.sales.models import Sale
            c_qs = Sale.objects.filter(contact=active_conv.contact).order_by('-created_at')
            if not c_qs.exists() and active_conv.contact.phone:
                c_qs = Sale.objects.filter(customer_phone=active_conv.contact.phone).order_by('-created_at')
            contact_orders = list(c_qs[:6])
            contact_order_count = c_qs.count()
            contact_total_spent = sum(o.grand_total for o in c_qs)

        from apps.products.models import Product
        available_products = Product.objects.filter(is_active=True).order_by('name')[:100]

        context.update({
            'page_title': 'Messages Hub',
            'conversations': conversations[:60],
            'active_conv': active_conv,
            'chat_messages': chat_messages,
            'platform_filter': platform_filter,
            'filter_type': filter_type,
            'search_query': search,
            'platform_counts': platform_counts,
            'total_unread': total_unread,
            'templates': MessageTemplate.objects.filter(is_active=True)[:20],
            'platforms': Platform.choices,
            'contact_orders': contact_orders,
            'contact_total_spent': contact_total_spent,
            'contact_order_count': contact_order_count,
            'products': available_products,
        })
        return context


# ─────────────────────────────────────────────────────────────────────────────
# SEND MESSAGE — AJAX endpoint
# ─────────────────────────────────────────────────────────────────────────────
class SendMessageView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        conv_id = data.get('conversation_id') or kwargs.get('conv_id')
        body = (data.get('body') or '').strip()

        if not conv_id or not body:
            return JsonResponse({'error': 'conversation_id and body are required.'}, status=400)

        conv = get_object_or_404(Conversation, pk=conv_id)

        from .services.dispatcher import send_message
        msg = send_message(conv, body, sent_by=request.user)

        return JsonResponse({
            'ok': True,
            'message': {
                'id': msg.pk,
                'body': msg.body,
                'direction': msg.direction,
                'created_at': msg.created_at.strftime('%H:%M'),
                'is_delivered': msg.is_delivered,
            }
        })


# ─────────────────────────────────────────────────────────────────────────────
# NEW CONVERSATION — Start a new conversation with a contact
# ─────────────────────────────────────────────────────────────────────────────
class NewConversationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        contact_id = request.POST.get('contact_id')
        platform = request.POST.get('platform', Platform.WHATSAPP)
        initial_msg = request.POST.get('message', '').strip()

        contact = get_object_or_404(Contact, pk=contact_id)
        conv, _ = Conversation.objects.get_or_create(
            contact=contact,
            platform=platform,
            status=Conversation.Status.OPEN,
            defaults={'platform_thread_id': f'manual-{contact_id}-{platform}'},
        )

        if initial_msg:
            from .services.dispatcher import send_message
            send_message(conv, initial_msg, sent_by=request.user)

        flash_messages.success(request, f'Conversation started with {contact.name}.')
        return redirect(f'/messaging/inbox/?conv={conv.pk}')


# ─────────────────────────────────────────────────────────────────────────────
# CONTACTS — CRM list
# ─────────────────────────────────────────────────────────────────────────────
class ContactsView(LoginRequiredMixin, ListView):
    template_name = 'messaging/contacts.html'
    model = Contact
    context_object_name = 'contacts'
    paginate_by = 40

    def get_queryset(self):
        qs = Contact.objects.filter(is_active=True).order_by('name')
        search = self.request.GET.get('q', '').strip()
        platform = self.request.GET.get('platform', '')
        tag = self.request.GET.get('tag', '')

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        if platform == 'whatsapp':
            qs = qs.exclude(whatsapp_number='')
        elif platform == 'messenger':
            qs = qs.exclude(messenger_id='')
        elif platform == 'telegram':
            qs = qs.exclude(telegram_id='')
        elif platform == 'instagram':
            qs = qs.exclude(instagram_id='')
        elif platform == 'email':
            qs = qs.exclude(email='')
        if tag:
            qs = qs.filter(tags__icontains=tag)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Contacts CRM'
        context['search_query'] = self.request.GET.get('q', '')
        context['platform_filter'] = self.request.GET.get('platform', '')
        context['total_contacts'] = Contact.objects.filter(is_active=True).count()
        return context


# ─────────────────────────────────────────────────────────────────────────────
# CONTACT DETAIL
# ─────────────────────────────────────────────────────────────────────────────
class ContactDetailView(LoginRequiredMixin, DetailView):
    template_name = 'messaging/contact_detail.html'
    model = Contact
    context_object_name = 'contact'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        context['page_title'] = contact.name
        context['conversations'] = contact.conversations.order_by('-updated_at')[:10]
        context['recent_messages'] = Message.objects.filter(
            conversation__contact=contact
        ).order_by('-created_at')[:20]
        context['platforms'] = Platform.choices

        # Contact Order History
        from apps.sales.models import Sale, PaymentMethod
        from apps.products.models import Product

        orders = Sale.objects.filter(contact=contact).order_by('-created_at')
        if not orders.exists() and contact.phone:
            orders = Sale.objects.filter(customer_phone=contact.phone).order_by('-created_at')

        context['orders'] = orders
        context['total_orders'] = orders.count()
        context['total_spent'] = sum(o.grand_total for o in orders)
        context['products'] = Product.objects.filter(is_active=True).order_by('name')[:50]
        context['payment_methods'] = PaymentMethod.CHOICES
        return context


# ─────────────────────────────────────────────────────────────────────────────
# CREATE / EDIT CONTACT
# ─────────────────────────────────────────────────────────────────────────────
class ContactCreateView(LoginRequiredMixin, View):
    template_name = 'messaging/contact_form.html'

    def get(self, request, pk=None):
        contact = get_object_or_404(Contact, pk=pk) if pk else None
        return render(request, self.template_name, {
            'page_title': 'Edit Contact' if contact else 'New Contact',
            'contact': contact,
            'platforms': Platform.choices,
        })

    def post(self, request, pk=None):
        contact = get_object_or_404(Contact, pk=pk) if pk else Contact()
        contact.name = request.POST.get('name', '').strip()
        contact.phone = request.POST.get('phone', '').strip()
        contact.email = request.POST.get('email', '').strip()
        contact.company = request.POST.get('company', '').strip()
        contact.notes = request.POST.get('notes', '').strip()
        contact.tags = request.POST.get('tags', '').strip()
        contact.whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        contact.messenger_id = request.POST.get('messenger_id', '').strip()
        contact.instagram_id = request.POST.get('instagram_id', '').strip()
        contact.telegram_id = request.POST.get('telegram_id', '').strip()
        contact.telegram_username = request.POST.get('telegram_username', '').strip()

        if not contact.name:
            flash_messages.error(request, 'Name is required.')
            return render(request, self.template_name, {'contact': contact, 'page_title': 'Contact'})

        if not pk:
            contact.created_by = request.user
        contact.save()
        flash_messages.success(request, f'Contact "{contact.name}" saved successfully.')
        return redirect(f'/messaging/contacts/{contact.pk}/')


class ContactDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        name = contact.name
        contact.is_active = False
        contact.save()
        flash_messages.success(request, f'Contact "{name}" archived.')
        return redirect('/messaging/contacts/')


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM CONFIGURATION VIEW
# ─────────────────────────────────────────────────────────────────────────────
class PlatformConfigView(LoginRequiredMixin, View):
    template_name = 'messaging/platform_config.html'

    def _require_admin(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            flash_messages.error(request, 'Admin access required.')
            return redirect('/messaging/inbox/')
        return None

    def get(self, request):
        redirect_response = self._require_admin(request)
        if redirect_response:
            return redirect_response

        configs = {p: None for p in Platform.values}
        for cfg in PlatformConfig.objects.all():
            configs[cfg.platform] = cfg

        return render(request, self.template_name, {
            'page_title': 'Messaging Platform Settings',
            'configs': configs,
            'platforms': Platform.choices,
        })

    def post(self, request):
        redirect_response = self._require_admin(request)
        if redirect_response:
            return redirect_response

        platform = request.POST.get('platform')
        if not platform:
            flash_messages.error(request, 'Platform is required.')
            return redirect('/messaging/platforms/')

        cfg, _ = PlatformConfig.objects.get_or_create(platform=platform)
        cfg.is_active = request.POST.get('is_active') == 'on'
        cfg.access_token = request.POST.get('access_token', '').strip()
        cfg.phone_number_id = request.POST.get('phone_number_id', '').strip()
        cfg.business_account_id = request.POST.get('business_account_id', '').strip()
        cfg.app_id = request.POST.get('app_id', '').strip()
        cfg.webhook_verify_token = request.POST.get('webhook_verify_token', '').strip()
        cfg.bot_token = request.POST.get('bot_token', '').strip()
        cfg.bot_username = request.POST.get('bot_username', '').strip()
        cfg.smtp_host = request.POST.get('smtp_host', 'smtp.gmail.com').strip()
        cfg.smtp_port = int(request.POST.get('smtp_port', 587) or 587)
        cfg.smtp_username = request.POST.get('smtp_username', '').strip()
        cfg.smtp_password = request.POST.get('smtp_password', '').strip()
        cfg.smtp_use_tls = request.POST.get('smtp_use_tls') == 'on'
        cfg.updated_by = request.user
        cfg.save()

        flash_messages.success(
            request, f'{cfg.get_platform_display()} configuration saved successfully.'
        )
        return redirect('/messaging/platforms/')


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOKS — Receive inbound messages from platforms
# ─────────────────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """Handles GET (verification) and POST (events) from Meta."""

    def get(self, request):
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        from .services import whatsapp_service
        result = whatsapp_service.verify_webhook(mode, token, challenge)
        if result:
            return HttpResponse(result, status=200)
        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse('Bad Request', status=400)

        from .services import whatsapp_service
        from .services.dispatcher import ingest_inbound

        msgs = whatsapp_service.parse_webhook_payload(payload)
        for m in msgs:
            ingest_inbound(
                platform=Platform.WHATSAPP,
                platform_thread_id=m['from_phone'],
                sender_identifier=m['from_phone'],
                sender_name='',
                body=m['body'],
                platform_message_id=m['wa_message_id'],
            )
        return HttpResponse('OK', status=200)


@method_decorator(csrf_exempt, name='dispatch')
class MessengerWebhookView(View):
    def get(self, request):
        from apps.messaging.models import PlatformConfig, Platform
        try:
            cfg = PlatformConfig.objects.get(platform=Platform.MESSENGER, is_active=True)
            mode = request.GET.get('hub.mode')
            token = request.GET.get('hub.verify_token')
            challenge = request.GET.get('hub.challenge')
            if mode == 'subscribe' and token == cfg.webhook_verify_token:
                return HttpResponse(challenge, status=200)
        except PlatformConfig.DoesNotExist:
            pass
        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse('Bad Request', status=400)

        from .services import messenger_service
        from .services.dispatcher import ingest_inbound

        msgs = messenger_service.parse_webhook_payload(payload)
        for m in msgs:
            ingest_inbound(
                platform=Platform.MESSENGER,
                platform_thread_id=m['sender_id'],
                sender_identifier=m['sender_id'],
                sender_name='',
                body=m['body'],
                platform_message_id=m['mid'],
            )
        return HttpResponse('OK', status=200)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse('Bad Request', status=400)

        from .services import telegram_service
        from .services.dispatcher import ingest_inbound

        msgs = telegram_service.parse_webhook_payload(payload)
        for m in msgs:
            ingest_inbound(
                platform=Platform.TELEGRAM,
                platform_thread_id=m['chat_id'],
                sender_identifier=m['chat_id'],
                sender_name=m.get('first_name', '') or m.get('username', ''),
                body=m['body'],
                platform_message_id=str(m['message_id']),
            )
        return HttpResponse('OK', status=200)


# ─────────────────────────────────────────────────────────────────────────────
# API — Fetch new messages for polling
# ─────────────────────────────────────────────────────────────────────────────
class ConversationMessagesAPIView(LoginRequiredMixin, View):
    """Returns JSON messages for a conversation (for polling)."""

    def get(self, request, conv_id):
        conv = get_object_or_404(Conversation, pk=conv_id)
        since_id = request.GET.get('since', 0)

        msgs = conv.messages.filter(pk__gt=since_id).order_by('created_at')
        data = [{
            'id': m.pk,
            'body': m.body,
            'direction': m.direction,
            'created_at': m.created_at.strftime('%H:%M'),
            'is_read': m.is_read,
        } for m in msgs]

        # Mark inbound as read
        conv.messages.filter(direction='inbound', is_read=False).update(is_read=True)
        conv.unread_count = 0
        conv.save(update_fields=['unread_count'])

        return JsonResponse({'messages': data, 'conv_id': conv_id})


class UnreadCountAPIView(LoginRequiredMixin, View):
    """Returns total unread conversation count."""

    def get(self, request):
        count = Conversation.objects.filter(unread_count__gt=0).count()
        return JsonResponse({'unread': count})
