"""
Sales URLs router.
"""
from django.urls import path
from .views import SaleListView, SaleDetailView, SaleCancelView, ReturnListView, CourierSettingsView, SteadfastWebhookView
from apps.messaging.views_order import SteadfastDispatchActionView, SteadfastStatusSyncActionView, SteadfastBalanceView

app_name = 'sales'

urlpatterns = [
    path('', SaleListView.as_view(), name='list'),
    path('<int:pk>/', SaleDetailView.as_view(), name='detail'),
    path('<int:pk>/cancel/', SaleCancelView.as_view(), name='cancel'),
    path('returns/', ReturnListView.as_view(), name='returns'),

    # ── Steadfast Courier Operations ─────────────────────────────────────────
    path('<int:sale_id>/courier/dispatch/', SteadfastDispatchActionView.as_view(), name='courier_dispatch'),
    path('<int:sale_id>/courier/sync/', SteadfastStatusSyncActionView.as_view(), name='courier_sync'),
    path('courier/settings/', CourierSettingsView.as_view(), name='courier_settings'),
    path('courier/balance/', SteadfastBalanceView.as_view(), name='courier_balance'),
    path('courier/webhook/', SteadfastWebhookView.as_view(), name='courier_webhook'),
]
