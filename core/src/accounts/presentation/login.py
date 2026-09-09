"""Compose existing login forms for progressive channel selection without side effects."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings

from accounts.forms import LoginForm, RequestLoginCodeForm
from accounts.services.capabilities import password_login_enabled


def channel_url(url, channel):
    """Preserve allauth's return URL while choosing a code-delivery channel."""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "channel"]
    query.append(("channel", channel))
    return urlunsplit(parts._replace(query=urlencode(query)))


def login_panels(request, form, mode, login_url, code_url):
    """Keep the bound form intact and prepare only enabled, unbound alternatives.

    Constructing an alternative never validates credentials, starts a login stage,
    or sends a code. Each panel retains its existing POST endpoint.
    """
    panels = []
    if password_login_enabled() or settings.EMAIL_CODE_LOGIN_ENABLED:
        email_code = mode == "email"
        panels.append(
            {
                "channel": "email",
                "label": "Email",
                "form": form if mode != "telegram" else LoginForm(request=request),
                "code": email_code,
                "href": channel_url(code_url, "email") if email_code else login_url,
            }
        )
    if settings.PHONE_LOGIN_ENABLED:
        panels.append(
            {
                "channel": "telegram",
                "label": "Телефон Telegram",
                "form": (
                    form
                    if mode == "telegram"
                    else RequestLoginCodeForm(channel="telegram")
                ),
                "code": True,
                "href": channel_url(code_url, "telegram"),
            }
        )
    for panel in panels:
        panel["active"] = panel["channel"] == (
            "telegram" if mode == "telegram" else "email"
        )
    return panels
