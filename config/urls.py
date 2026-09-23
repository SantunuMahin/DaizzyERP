"""
URL configuration for Daizzy IMS.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Root redirect to dashboard
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),
    
    # Web UI Apps
    path('dashboard/', include('apps.core.urls')),
    path('users/', include('apps.users.urls', namespace='users')),
    path('products/', include('apps.products.urls', namespace='products')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('pos/', include('apps.pos.urls', namespace='pos')),
    path('sales/', include('apps.sales.urls', namespace='sales')),
    path('invoices/', include('apps.invoices.urls', namespace='invoices')),
    path('barcode/', include('apps.barcode.urls', namespace='barcode')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('settings/', include('apps.settings_app.urls', namespace='settings_app')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
    
    # Versioned REST API
    path('api/v1/', include('apps.api.v1.urls', namespace='api_v1')),

    # Communications Hub — Messages & Contacts
    path('messaging/', include('apps.messaging.urls', namespace='messaging')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
