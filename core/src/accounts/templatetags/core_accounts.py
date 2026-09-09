"""Thin template bindings for account presentation and versioned UI assets."""

from django import template

from accounts.presentation.fields import serialize_field
from accounts.presentation.social_accounts import social_account_label

register = template.Library()
register.filter("social_account_label", social_account_label)


@register.filter
def device_label(user_agent):
    """Describe a session for display; user-agent claims never grant trust."""
    agent = str(user_agent or "").lower()
    browser = ""
    for tokens, label in (
        (("edg/", "edga/", "edgios/"), "Edge"),
        (("opr/", "opera/"), "Opera"),
        (("samsungbrowser/",), "Samsung Internet"),
        (("firefox/", "fxios/"), "Firefox"),
        (("chrome/", "crios/", "chromium/"), "Chrome"),
        (("safari/",), "Safari"),
    ):
        if any(token in agent for token in tokens):
            browser = label
            break

    if "ipad" in agent or ("macintosh" in agent and "mobile/" in agent):
        platform = "iPadOS"
    elif "iphone" in agent or "ipod" in agent:
        platform = "iOS"
    elif "android" in agent:
        platform = "Android"
    elif "cros" in agent:
        platform = "ChromeOS"
    elif "windows" in agent:
        platform = "Windows"
    elif "macintosh" in agent or "mac os x" in agent:
        platform = "macOS"
    elif "linux" in agent:
        platform = "Linux"
    else:
        platform = ""

    return (
        " · ".join(part for part in (browser, platform) if part)
        or "Неизвестное устройство"
    )


@register.inclusion_tag("accounts/ui/fields.html")
def core_fields(form, exclude=""):
    """Render visible form fields while preserving the native HTML fallback."""
    return {
        "form": form,
        "fields": [field for field in form.visible_fields() if field.name != exclude],
    }


@register.inclusion_tag("accounts/ui/field.html")
def core_field(field):
    """Render one bound field with its native errors and optional Vue enhancement."""
    return {"field": field}


@register.filter
def field_schema(field):
    """Adapt a bound field for the safe json_script payload used by Vue."""
    return serialize_field(field)


@register.simple_tag
def accounts_assets():
    """Vite owns content hashes; Django static storage owns deployment URLs."""
    import json
    from pathlib import Path
    from django.conf import settings
    from django.templatetags.static import static
    from django.utils.html import format_html_join

    manifest = Path(settings.BASE_DIR) / "src/accounts/static/core/ui/manifest.json"
    if not manifest.exists():
        return ""
    entry = json.loads(manifest.read_text())["src/django/main.ts"]
    styles = format_html_join(
        "\n",
        '<link rel="stylesheet" href="{}">',
        ((static("core/ui/" + css),) for css in entry.get("css", [])),
    )
    from django.utils.html import format_html

    return format_html(
        '{}\n<script type="module" src="{}"></script>',
        styles,
        static("core/ui/" + entry["file"]),
    )
