"""
Invoice URLs router.
"""
from django.urls import path
from .views import InvoiceListView, InvoiceDetailView, InvoicePrintView

app_name = 'invoices'

urlpatterns = [
    path('', InvoiceListView.as_view(), name='list'),
    path('<int:pk>/', InvoiceDetailView.as_view(), name='detail'),
    path('<int:pk>/print/', InvoicePrintView.as_view(), name='print'),
]
