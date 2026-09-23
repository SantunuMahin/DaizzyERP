"""
Barcode URLs router.
"""
from django.urls import path
from .views import BarcodePrintLabelsView, BarcodeImageServeView

app_name = 'barcode'

urlpatterns = [
    path('labels/', BarcodePrintLabelsView.as_view(), name='print_labels'),
    path('svg/<str:barcode_value>/', BarcodeImageServeView.as_view(), name='svg'),
]
