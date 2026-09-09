"""Plain-text labels for identifying saved social profiles without provider access."""

PROVIDER_NAMES = {"telegram": "Telegram", "github": "GitHub", "google": "Google"}


def _text(value):
    """Accept display strings only, normalizing whitespace without trusting markup."""
    return " ".join(value.split()) if isinstance(value, str) else ""


def social_account_label(account):
    """Describe a saved profile using whitelisted public fields and a stable ID.

    The result is ordinary text: Django templates and Vue's field serialization
    retain their normal escaping. Disabled providers need no runtime credentials
    to display a saved connection, and arbitrary metadata is never stringified.
    """
    data = account.extra_data if isinstance(account.extra_data, dict) else {}
    provider = account.provider
    name = PROVIDER_NAMES.get(provider, _text(provider) or "Внешний аккаунт")
    uid = _text(account.uid)
    if provider == "telegram":
        username = _text(data.get("username")) or _text(data.get("preferred_username"))
        if username:
            identity = f"@{username.lstrip('@')}"
        else:
            subject = _text(data.get("sub")) or uid
            display_name = _text(data.get("name"))
            identity = " · ".join(
                part for part in (display_name, f"ID {subject}") if part
            )
    elif provider == "github" and (username := _text(data.get("login"))):
        identity = f"@{username.lstrip('@')}"
    elif provider == "google" and (email := _text(data.get("email"))):
        identity = email
    else:
        identity = f"ID {uid}"
    return f"{name} · {identity}"
