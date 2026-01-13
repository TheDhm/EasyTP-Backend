from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Database for development (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles' 

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development-specific apps
# INSTALLED_APPS += [
#     'django_extensions',  # Optional: useful development tools
#     'debug_toolbar',      # Optional: debugging toolbar
# ]

# Debug toolbar middleware (if using debug_toolbar)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

# Add admin localhost restriction middleware
MIDDLEWARE += ['main.middleware.AdminLocalhostMiddleware']

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://api.melekabderrahmane.com",
    "http://localhost:5173",  # For React development
    "http://127.0.0.1:5173",
    "http://localhost:8000",  # For Django development
]