"""
POS URLs routing.
"""
from django.urls import path
from .views import POSTerminalView

app_name = 'pos'

urlpatterns = [
    path('', POSTerminalView.as_view(), name='terminal'),
]
