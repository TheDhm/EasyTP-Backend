import os

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Configure this properly for production
ALLOWED_HOSTS = [
    "https://api.melekabderrahmane.com",
    "https://easytp.melekabderrahmane.com",
    "easytp.melekabderrahmane.com",
    "api.melekabderrahmane.com",
    "django-service",  # Kubernetes service name
    "django-service.django-app",  # Service with namespace
    "django-service.django-app.svc.cluster.local",
    "localhost",
    "195.201.32.187",
]


# Database for production (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "django_db"),
        "USER": os.environ.get("DB_USER", "django_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,  # Keep connections alive for 10 minutes
        "CONN_HEALTH_CHECKS": True,  # Test connections before use (Django 4.1+)
    }
}

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media/"

# Security settings for production
# SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = "same-origin"

CSRF_TRUSTED_ORIGINS = [
    "https://api.melekabderrahmane.com",
    "https://easytp.melekabderrahmane.com",
    "https://195.201.32.187",
]

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# # Email settings for production
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@your-domain.com')

# Redis Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis-service.django-app.svc.cluster.local:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 20,
                "retry_on_timeout": True,
            },
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
        "TIMEOUT": 300,  # 5 minutes
        "KEY_PREFIX": "django_cache",
    }
}

# Session Configuration - Use Redis for sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False

# Add admin localhost restriction middleware
MIDDLEWARE += ["main.middleware.AdminLocalhostMiddleware"]


# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://api.melekabderrahmane.com",
    "https://easytp.melekabderrahmane.com",
]
