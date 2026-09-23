"""
Reports URLs router.
"""
from django.urls import path
from .views import SalesReportView, InventoryReportView

app_name = 'reports'

urlpatterns = [
    path('sales/', SalesReportView.as_view(), name='sales'),
    path('inventory/', InventoryReportView.as_view(), name='inventory'),
]
