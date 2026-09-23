"""
Auto Messaging Rules View.
Manage and configure event triggers (Order Confirmation, Steadfast Dispatch, Delivered, Tracking Bot).
"""
import logging
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib import messages as flash_messages

from apps.messaging.models import MessageTemplate, Platform
from apps.messaging.services.auto_messaging import DEFAULT_TEMPLATES

logger = logging.getLogger(__name__)

EVENT_LABELS = [
    ('ORDER_CONFIRMED', 'Order Confirmation', 'Sent immediately when an order is placed/confirmed via online or messaging.'),
    ('COURIER_DISPATCHED', 'Steadfast Courier Dispatched', 'Sent when the order is booked on Steadfast with tracking code & live link.'),
    ('ORDER_DELIVERED', 'Order Delivered Successfully', 'Sent upon parcel delivery completion or review request.'),
    ('ORDER_CANCELLED', 'Order Cancelled', 'Sent when an order is cancelled or refunded.'),
    ('TRACKING_BOT_REPLY', 'Inbound Order Tracking Bot', 'Auto-replied when customer types "track", "order", "status" or invoice number.'),
]


class AutoMessagingRulesView(LoginRequiredMixin, View):
    """Configuration panel for automated notification templates."""
    template_name = 'messaging/auto_rules.html'

    def get(self, request):
        rules = []
        for code, label, desc in EVENT_LABELS:
            cat = f"auto_{code.lower()}"
            tpl = MessageTemplate.objects.filter(category=cat).first()
            current_body = tpl.body if tpl else DEFAULT_TEMPLATES.get(code, '')
            is_active = tpl.is_active if tpl else True
            rules.append({
                'code': code,
                'label': label,
                'description': desc,
                'body': current_body,
                'is_active': is_active,
                'template_id': tpl.pk if tpl else None,
            })

        return render(request, self.template_name, {
            'page_title': 'Automated Messaging Rules',
            'rules': rules,
        })

    def post(self, request):
        rule_code = request.POST.get('rule_code')
        body = request.POST.get('body', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not rule_code:
            flash_messages.error(request, 'Rule code is missing.')
            return redirect('messaging:auto_rules')

        cat = f"auto_{rule_code.lower()}"
        label_dict = dict([(c, l) for c, l, _ in EVENT_LABELS])
        tpl_name = label_dict.get(rule_code, rule_code)

        tpl, _ = MessageTemplate.objects.get_or_create(
            category=cat,
            defaults={'name': tpl_name, 'created_by': request.user}
        )
        tpl.body = body or DEFAULT_TEMPLATES.get(rule_code, '')
        tpl.is_active = is_active
        tpl.save()

        flash_messages.success(request, f'Automated rule "{tpl_name}" updated successfully.')
        return redirect('messaging:auto_rules')
