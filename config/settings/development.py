"""
Development settings for Daizzy IMS.
"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Disable strict manifest static storage in development to ease asset editing
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Allow all origins in local dev if needed
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
