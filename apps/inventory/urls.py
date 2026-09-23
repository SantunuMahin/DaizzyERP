"""
Inventory URLs router.
"""
from django.urls import path
from .views import StockOverviewView, StockAdjustmentView, InventoryTransactionListView

app_name = 'inventory'

urlpatterns = [
    path('', StockOverviewView.as_view(), name='overview'),
    path('adjust/', StockAdjustmentView.as_view(), name='adjust'),
    path('transactions/', InventoryTransactionListView.as_view(), name='transactions'),
]
