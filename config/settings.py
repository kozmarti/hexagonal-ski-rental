import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "dev-only-insecure-key"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# JSON API keys, one per device, comma-separated. Empty means the API refuses every request.
API_KEYS = [key.strip() for key in os.environ.get("API_KEYS", "").split(",") if key.strip()]

# Address printed in the QR stickers, reachable by the phones scanning them, e.g.
# http://192.168.1.20:8000. Empty: the address of the page printing the labels is used.
LABELS_BASE_URL = os.environ.get("LABELS_BASE_URL", "")

# Where the rental data lives: "orm" (PostgreSQL, through Django) or "mongo" (MongoDB).
# Only bootstrap.py reads it, to choose the repository adapters.
REPOSITORY_BACKEND = os.environ.get("REPOSITORY_BACKEND", "orm")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongo:27017/?directConnection=true")
MONGO_DB = os.environ.get("MONGO_DB", "ski_rental")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # Django only knows about the adapters, never the core.
    "rental.adapters.outbound.orm.apps.OrmConfig",
    "rental.adapters.inbound.web.apps.WebConfig",
    "config.apps.DevToolsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ski_rental"),
        "USER": os.environ.get("POSTGRES_USER", "ski_rental"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "ski_rental"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
