import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config import env

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "dev-only-insecure-key"
ALLOWED_HOSTS = env.allowed_hosts(os.environ)

# Behind the host's HTTPS proxy (the hosted demo): the proxy says the visitor used HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # the host's own health check, over plain HTTP
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Not preloaded in browsers: that would bind the whole domain, not only this app.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

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

# Which notifiers receive the events: "logging", "email", or both ("logging,email").
# Only bootstrap.py reads it.
NOTIFIERS = [
    name.strip() for name in os.environ.get("NOTIFIERS", "logging").split(",") if name.strip()
]
# The email notifier writes to the shop: customers have no email address yet.
SHOP_EMAIL = os.environ.get("SHOP_EMAIL", "shop@example.com")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "ski-rental@example.com")
# In development, Mailpit (docker-compose) catches every email: http://localhost:8025
EMAIL_HOST = os.environ.get("EMAIL_HOST", "mailpit")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_TIMEOUT = 5

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

DATABASES = {"default": env.database(os.environ)}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": env.static_files_storage(STATIC_ROOT, os.environ)},
}
# In the production image (static files collected), WhiteNoise serves them itself: no extra
# server. In development, runserver serves them from the apps' static folders.
if STATIC_ROOT.is_dir():
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

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
