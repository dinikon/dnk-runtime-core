"""Django integration settings; configurable values originate in typed CORE config."""

from .config import CORE_DIR, load_config
from .configuration.allauth import authentication_settings, social_settings
from .configuration.django import application_settings, infrastructure_settings

BASE_DIR = CORE_DIR
_config = load_config()

# These projections form Django's settings namespace. Application code reads
# django.conf.settings, so test overrides and allauth keep their normal contract.
globals().update(application_settings(_config))
globals().update(infrastructure_settings(_config, BASE_DIR))
globals().update(authentication_settings(_config))
globals().update(social_settings(_config))

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
            ]
        },
    }
]
WSGI_APPLICATION = "dnk_core.wsgi.application"
ASGI_APPLICATION = "dnk_core.asgi.application"

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
ACCOUNT_USER_DISPLAY = "accounts.presentation.profile.user_display"

# Security invariants intentionally have no environment switch.
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_LOGIN_BY_CODE_REQUIRED = False
ACCOUNT_PHONE_VERIFICATION_ENABLED = True
ACCOUNT_PHONE_VERIFICATION_CODE_FORMAT = {"numeric": True, "dashed": False, "length": 6}
ACCOUNT_LOGIN_BY_CODE_FORMAT = {"numeric": True, "dashed": False, "length": 6}
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT = {
    "numeric": True,
    "dashed": False,
    "length": 6,
}
ACCOUNT_REAUTHENTICATION_REQUIRED = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/"

MFA_ADAPTER = "accounts.adapters.MFAAdapter"
# Enrollment flags never remove verification support for existing factors.
MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]
MFA_ALLOW_UNVERIFIED_EMAIL = False
MFA_RECOVERY_CODES_SHOW_ONCE = True
MFA_TRUST_ENABLED = False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = False
MFA_FORMS = {
    "add_webauthn": "accounts.forms.AddPasskeyForm",
    "login_webauthn": "accounts.forms.LoginPasskeyForm",
    "signup_webauthn": "accounts.forms.SignupPasskeyForm",
}
USERSESSIONS_TRACK_ACTIVITY = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_FORMS = {
    "disconnect": "accounts.forms.DisconnectForm",
    "signup": "accounts.forms.SocialSignupForm",
}
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_STORE_TOKENS = False

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_NAME = "dnk_core_sessionid"
CSRF_COOKIE_NAME = "dnk_core_csrftoken"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
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
