"""
Test settings for freight_transport project.
Optimized for fast test execution and isolation.
"""

from .base import *

# Security
SECRET_KEY = "django-insecure-test-key-only-for-testing"

# Django automatically sets DEBUG=False during testing
# but we'll be explicit about it
DEBUG = False

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use dummy cache backend for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Test-specific DRF settings
REST_FRAMEWORK.update(
    {
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
            # Remove BrowsableAPIRenderer for tests
        ],
        "TEST_REQUEST_DEFAULT_FORMAT": "json",
    }
)

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",  # Fast but insecure - only for tests
]

# Disable CORS checks in tests
CORS_ALLOW_ALL_ORIGINS = True

# Session configuration for tests
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Never load debug toolbar in tests
# Django sets DEBUG=False automatically, but we ensure no debug toolbar components are loaded
