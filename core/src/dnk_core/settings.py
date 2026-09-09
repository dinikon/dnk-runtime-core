"""Standalone Django settings; load core/.env explicitly through the launcher."""

import base64
import hashlib
import os
from pathlib import Path
from urllib.parse import quote, urlsplit

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("CORE_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("Set CORE_SECRET_KEY before starting Core.")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes"}


DEBUG = env_bool("CORE_DEBUG")
PUBLIC_ORIGIN = os.environ.get(
    "CORE_PUBLIC_ORIGIN", "http://localhost:8000" if DEBUG else ""
).rstrip("/")
origin = urlsplit(PUBLIC_ORIGIN)
if (
    not origin.hostname
    or origin.scheme not in {"http", "https"}
    or origin.path
    or origin.query
    or origin.fragment
    or origin.username
    or origin.password
    or (not DEBUG and origin.scheme != "https")
):
    raise ImproperlyConfigured(
        "Set CORE_PUBLIC_ORIGIN to the public origin (HTTPS in production)."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("CORE_ALLOWED_HOSTS", origin.hostname).split(",")
    if host.strip()
]
if not DEBUG and ("*" in ALLOWED_HOSTS or origin.hostname not in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "CORE_ALLOWED_HOSTS must include the public hostname and cannot contain '*'."
    )

MFA_ENCRYPTION_KEY = os.environ.get("CORE_MFA_ENCRYPTION_KEY", "")
if not MFA_ENCRYPTION_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set CORE_MFA_ENCRYPTION_KEY in production.")
    # Stable for a development database. Production uses an independent key.
    MFA_ENCRYPTION_KEY = base64.urlsafe_b64encode(
        hashlib.sha256(("dnk-core-development-mfa:" + SECRET_KEY).encode()).digest()
    ).decode()
try:
    Fernet(MFA_ENCRYPTION_KEY)
except (ValueError, TypeError):
    raise ImproperlyConfigured(
        "CORE_MFA_ENCRYPTION_KEY must be a valid Fernet key."
    ) from None

TELEGRAM_GATEWAY_TOKEN = os.environ.get("CORE_TELEGRAM_GATEWAY_TOKEN", "")
TELEGRAM_GATEWAY_TIMEOUT = float(os.environ.get("CORE_TELEGRAM_GATEWAY_TIMEOUT", "5"))
PHONE_LOGIN_ENABLED = env_bool(
    "CORE_TELEGRAM_GATEWAY_ENABLED", bool(TELEGRAM_GATEWAY_TOKEN)
) and bool(TELEGRAM_GATEWAY_TOKEN)
GOOGLE_CLIENT_ID = os.environ.get("CORE_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("CORE_GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.environ.get("CORE_GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("CORE_GITHUB_CLIENT_SECRET", "")
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
GITHUB_LOGIN_ENABLED = bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
TELEGRAM_LOGIN_CLIENT_ID = os.environ.get("CORE_TELEGRAM_LOGIN_CLIENT_ID", "")
TELEGRAM_LOGIN_CLIENT_SECRET = os.environ.get("CORE_TELEGRAM_LOGIN_CLIENT_SECRET", "")
TELEGRAM_LOGIN_ENABLED = bool(TELEGRAM_LOGIN_CLIENT_ID and TELEGRAM_LOGIN_CLIENT_SECRET)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.mfa",
    "allauth.usersessions",
    "allauth.socialaccount.providers.openid_connect",
]
if GOOGLE_LOGIN_ENABLED:
    INSTALLED_APPS.append("allauth.socialaccount.providers.google")
if GITHUB_LOGIN_ENABLED:
    INSTALLED_APPS.append("allauth.socialaccount.providers.github")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.middleware.SocialOnlyReauthenticationMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dnk_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.account_features",
            ],
        },
    },
]

WSGI_APPLICATION = "dnk_core.wsgi.application"
ASGI_APPLICATION = "dnk_core.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("CORE_DB_NAME", "dniko"),
        "USER": os.environ.get("CORE_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("CORE_DB_PASSWORD", ""),
        "HOST": os.environ.get("CORE_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("CORE_DB_PORT", "5432"),
        # No public fallback: Django tables and its migration history belong to Core.
        "OPTIONS": {"options": "-c search_path=core"},
    },
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
ACCOUNT_FORMS = {
    "request_login_code": "accounts.forms.RequestLoginCodeForm",
    "login": "accounts.forms.LoginForm",
    "signup": "accounts.forms.SignupForm",
}
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = [
    "username*",
    "email*",
    "password1*",
    "password2*"
]
if PHONE_LOGIN_ENABLED:
    ACCOUNT_LOGIN_METHODS.add("phone")
    ACCOUNT_SIGNUP_FIELDS.append("phone")
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_REQUIRED = False
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 300
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 3
ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND = True
ACCOUNT_PHONE_VERIFICATION_ENABLED = True
ACCOUNT_PHONE_VERIFICATION_TIMEOUT = 300
ACCOUNT_PHONE_VERIFICATION_MAX_ATTEMPTS = 3
ACCOUNT_PHONE_VERIFICATION_SUPPORTS_RESEND = True
ACCOUNT_PHONE_VERIFICATION_CODE_FORMAT = {"numeric": True, "dashed": False, "length": 6}
ACCOUNT_LOGIN_BY_CODE_FORMAT = {"numeric": True, "dashed": False, "length": 6}
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT = {
    "numeric": True,
    "dashed": False,
    "length": 6,
}
ACCOUNT_REAUTHENTICATION_REQUIRED = True
ACCOUNT_REAUTHENTICATION_TIMEOUT = 300
ACCOUNT_RATE_LIMITS = {"core_email_reauthenticate": "1/30s/user,5/h/user"}
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = None
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[dNiko Alpha] "
ACCOUNT_EMAIL_NOTIFICATIONS = True
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/"

MFA_ADAPTER = "accounts.adapters.MFAAdapter"
MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]
MFA_PASSKEY_LOGIN_ENABLED = True
MFA_PASSKEY_SIGNUP_ENABLED = True
MFA_ALLOW_UNVERIFIED_EMAIL = False
MFA_RECOVERY_CODES_SHOW_ONCE = True
MFA_TOTP_ISSUER = "dNiko Alpha"
MFA_TRUST_ENABLED = False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = False
MFA_FORMS = {
    "add_webauthn": "accounts.forms.AddPasskeyForm",
    "login_webauthn": "accounts.forms.LoginPasskeyForm",
    "signup_webauthn": "accounts.forms.SignupPasskeyForm",
}
USERSESSIONS_TRACK_ACTIVITY = True
ALLAUTH_TRUSTED_PROXY_COUNT = int(os.environ.get("CORE_TRUSTED_PROXY_COUNT", "0"))
if ALLAUTH_TRUSTED_PROXY_COUNT < 0:
    raise ImproperlyConfigured("CORE_TRUSTED_PROXY_COUNT cannot be negative.")

SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_FORMS = {"disconnect": "accounts.forms.DisconnectForm"}
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {}
if TELEGRAM_LOGIN_ENABLED:
    SOCIALACCOUNT_PROVIDERS["openid_connect"] = {
        "APPS": [
            {
                "provider_id": "telegram",
                "name": "Telegram",
                "client_id": TELEGRAM_LOGIN_CLIENT_ID,
                "secret": TELEGRAM_LOGIN_CLIENT_SECRET,
                "settings": {
                    "server_url": "https://oauth.telegram.org",
                    "token_auth_method": "client_secret_basic",
                    "scope": ["openid", "profile"],
                    "oauth_pkce_enabled": True,
                    "fetch_userinfo": False,
                },
            }
        ],
    }
if GOOGLE_LOGIN_ENABLED:
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [
            {"client_id": GOOGLE_CLIENT_ID, "secret": GOOGLE_CLIENT_SECRET, "key": ""}
        ],
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    }
if GITHUB_LOGIN_ENABLED:
    SOCIALACCOUNT_PROVIDERS["github"] = {
        "APPS": [
            {"client_id": GITHUB_CLIENT_ID, "secret": GITHUB_CLIENT_SECRET, "key": ""}
        ],
        "SCOPE": ["user:email"],
    }

REDIS_URL = os.environ.get("CORE_REDIS_URL", "")
redis_host = os.environ.get("CORE_REDIS_HOST", "")
if not REDIS_URL and redis_host:
    redis_password = os.environ.get("CORE_REDIS_PASSWORD", "")
    redis_auth = f":{quote(redis_password, safe='')}@" if redis_password else ""
    REDIS_URL = (
        f"redis://{redis_auth}{redis_host}:"
        f"{int(os.environ.get('CORE_REDIS_PORT', '6379'))}/"
        f"{int(os.environ.get('CORE_REDIS_DB', '2'))}"
    )
if REDIS_URL:
    if urlsplit(REDIS_URL).scheme not in {"redis", "rediss"}:
        raise ImproperlyConfigured("CORE_REDIS_URL must use redis:// or rediss://.")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "dnk:core",
        }
    }
elif DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dnk-core-development",
            "KEY_PREFIX": "dnk:core",
        }
    }
else:
    raise ImproperlyConfigured(
        "Set CORE_REDIS_URL or CORE_REDIS_HOST for shared production rate limits."
    )

EMAIL_BACKEND = os.environ.get(
    "CORE_EMAIL_BACKEND",
    (
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)
EMAIL_HOST = os.environ.get("CORE_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("CORE_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("CORE_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("CORE_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("CORE_EMAIL_USE_TLS", not DEBUG)
EMAIL_USE_SSL = env_bool("CORE_EMAIL_USE_SSL")
EMAIL_VERIFY_CERTIFICATE = env_bool("CORE_EMAIL_VERIFY_CERTIFICATE", True)
if not EMAIL_VERIFY_CERTIFICATE and not DEBUG:
    raise ImproperlyConfigured(
        "CORE_EMAIL_VERIFY_CERTIFICATE=false is allowed only with CORE_DEBUG=true."
    )
EMAIL_FILE_PATH = os.environ.get("CORE_EMAIL_FILE_PATH", str(BASE_DIR / "mail-outbox"))
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get(
    "CORE_DEFAULT_FROM_EMAIL", "dNiko Alpha <noreply@localhost>"
)

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Separate names also isolate local cookies from the runtime on another port.
SESSION_COOKIE_NAME = "dnk_core_sessionid"
CSRF_COOKIE_NAME = "dnk_core_csrftoken"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_ENGINE = "django.contrib.sessions.backends.db"
CSRF_TRUSTED_ORIGINS = [PUBLIC_ORIGIN]
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if env_bool("CORE_TRUST_PROXY"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
