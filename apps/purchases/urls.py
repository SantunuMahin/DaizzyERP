from django.urls import path
from .views import (
    PurchaseListView,
    PurchaseCreateView,
    PurchaseDetailView,
    PurchaseProductsAnalysisView,
)

app_name = 'purchases'

urlpatterns = [
    path('', PurchaseListView.as_view(), name='list'),
    path('create/', PurchaseCreateView.as_view(), name='create'),
    path('<int:pk>/', PurchaseDetailView.as_view(), name='detail'),
    path('analysis/', PurchaseProductsAnalysisView.as_view(), name='analysis'),
]
