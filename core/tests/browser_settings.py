"""Opt-in browser settings mounted only by compose.e2e.yml, never shipped in images."""

from django.core.exceptions import ImproperlyConfigured
from dnk_core.settings import *  # noqa: F403

if (
    not DEBUG or EMAIL_BACKEND != "django.core.mail.backends.filebased.EmailBackend"
):  # noqa: F405
    raise ImproperlyConfigured("Browser settings require DEBUG and isolated file mail.")

ACCOUNT_ADAPTER = "tests.browser_adapter.BrowserAccountAdapter"
# Browser tests exercise interactions without waiting for delivery cooldowns.
# Backend and PostgreSQL tests separately exercise the unchanged production limits.
ACCOUNT_RATE_LIMITS = {  # noqa: F405
    **ACCOUNT_RATE_LIMITS,
    "change_phone": "100/m/user",
    "verify_phone": "100/m/key,100/m/ip",
    "request_login_code": "100/m/key,100/m/ip",
}
