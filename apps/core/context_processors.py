"""
Context processors providing global business variables to templates.
"""
from django.conf import settings


def global_settings(request):
    """
    Exposes store branding, currency symbols, and active user role helpers.
    """
    user = request.user
    role = getattr(user, 'role', '') if user.is_authenticated else ''

    # Lazy import of StoreSettings to avoid circular imports during app initialization
    store_name = 'Daizzy.online'
    currency_symbol = settings.DEFAULT_CURRENCY_SYMBOL
    currency = settings.DEFAULT_CURRENCY

    try:
        from apps.settings_app.models import StoreSettings
        st = StoreSettings.get_settings()
        store_name = st.store_name
        currency_symbol = st.currency_symbol
        currency = st.currency
    except Exception:
        pass

    return {
        'STORE_NAME': store_name,
        'CURRENCY': currency,
        'CURRENCY_SYMBOL': currency_symbol,
        'USER_ROLE': role,
        'IS_ADMIN_ROLE': role in ['SUPER_ADMIN', 'ADMIN'] or (user.is_authenticated and user.is_superuser),
        'IS_MANAGER_ROLE': role in ['SUPER_ADMIN', 'ADMIN', 'MANAGER'] or (user.is_authenticated and user.is_superuser),
        'IS_INVENTORY_MGR_ROLE': role in ['SUPER_ADMIN', 'ADMIN', 'MANAGER', 'INVENTORY_MANAGER'] or (user.is_authenticated and user.is_superuser),
        'IS_CASHIER_ROLE': role in ['SUPER_ADMIN', 'ADMIN', 'MANAGER', 'CASHIER'] or (user.is_authenticated and user.is_superuser),
    }
