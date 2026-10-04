"""Django settings for Space City Sprouts."""
import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.brand",
                "shop.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("CONTACT_EMAIL", "hello@spacecitysprouts.com")

# ---------------------------------------------------------------------------
# Business
# ---------------------------------------------------------------------------
BRAND_NAME = os.environ.get("BRAND_NAME", "Space City Sprouts")
BRAND_TAGLINE = "Houston-grown organic microgreens, harvested to order."
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "hello@spacecitysprouts.com")
CONTACT_PHONE = os.environ.get("CONTACT_PHONE", "")
PICKUP_ADDRESS = os.environ.get(
    "PICKUP_ADDRESS", "Houston, TX — exact pickup address shared after you order."
)
SERVICE_AREA_LABEL = "Greater Houston, Texas"

# ---------------------------------------------------------------------------
# Delivery — edit DELIVERY_ZIPS to match the neighborhoods you serve.
# ---------------------------------------------------------------------------
_DEFAULT_ZIPS = [
    "77002", "77003", "77004", "77005", "77006", "77007", "77008", "77009",
    "77010", "77011", "77012", "77013", "77014", "77015", "77016", "77017",
    "77018", "77019", "77020", "77021", "77022", "77023", "77024", "77025",
    "77026", "77027", "77028", "77029", "77030", "77031", "77033", "77034",
    "77035", "77036", "77037", "77038", "77040", "77041", "77042", "77043",
    "77044", "77045", "77046", "77047", "77048", "77049", "77051", "77053",
    "77054", "77055", "77056", "77057", "77059", "77060", "77061", "77062",
    "77063", "77064", "77065", "77066", "77067", "77068", "77069", "77070",
    "77071", "77072", "77073", "77074", "77075", "77076", "77077", "77078",
    "77079", "77080", "77081", "77082", "77083", "77084", "77085", "77086",
    "77087", "77088", "77089", "77090", "77091", "77092", "77093", "77094",
    "77095", "77096", "77098", "77099",
]
DELIVERY_ZIPS = [
    z.strip()
    for z in os.environ.get("DELIVERY_ZIPS", ",".join(_DEFAULT_ZIPS)).split(",")
    if z.strip()
]
DELIVERY_FEE = Decimal(os.environ.get("DELIVERY_FEE", "4.95"))
FREE_DELIVERY_MINIMUM = Decimal(os.environ.get("FREE_DELIVERY_MINIMUM", "35.00"))

# ---------------------------------------------------------------------------
# Stripe — leave blank until ready; checkout falls back to pay on
# pickup/delivery when no secret key is configured.
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# GitHub push-to-deploy webhook — shared secret for the /deploy/github/ hook.
# ---------------------------------------------------------------------------
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Email — transactional mail via the server's Plesk mail (SPF/DKIM/DMARC in DNS).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "hello@spacecitysprouts.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Space City Sprouts <hello@spacecitysprouts.com>"
)
# Order notifications: to + cc
STAFF_ORDER_EMAIL = os.environ.get("STAFF_ORDER_EMAIL", "Iqbal_abi@yahoo.com")
STAFF_ORDER_CC = [
    e.strip()
    for e in os.environ.get("STAFF_ORDER_CC", "ghazanfarali23@gmail.com").split(",")
    if e.strip()
]
