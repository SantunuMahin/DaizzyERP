"""
Settings app URL router.
"""
from django.urls import path
from .views import StoreSettingsUpdateView

app_name = 'settings_app'

urlpatterns = [
    path('', StoreSettingsUpdateView.as_view(), name='index'),
]
