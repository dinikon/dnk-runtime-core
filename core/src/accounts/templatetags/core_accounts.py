"""Thin template bindings for account presentation and versioned UI assets."""

from django import template

from accounts.presentation.fields import serialize_field
from accounts.presentation.social_accounts import social_account_label
from accounts.presentation.login import channel_url, login_panels

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
def field_schema(field, suppress_help=False):
    """Adapt a bound field for the safe json_script payload used by Vue."""
    return serialize_field(field, suppress_help=bool(suppress_help))


@register.inclusion_tag("accounts/ui/fields.html")
def core_signup_fields(form):
    """Group existing signup fields in visual and keyboard order without rebinding."""
    data = core_fields(form)
    order = {
        name: index
        for index, name in enumerate(
            (
                "last_name",
                "first_name",
                "middle_name",
                "email",
                "username",
                "password1",
                "password2",
                "phone",
            )
        )
    }
    data["fields"].sort(key=lambda field: order.get(field.name, len(order)))
    data["signup_layout"] = True
    return data


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


@register.inclusion_tag("accounts/ui/login_panels.html", takes_context=True)
def core_login_panels(context, form, mode="login"):
    """Render channel alternatives around the active view's native bound form."""
    data = context.flatten()
    code_url = context.get("request_login_code_url", "")
    data["login_panels"] = login_panels(
        context["request"], form, mode, context["login_url"], code_url
    )
    data["email_code_url"] = channel_url(code_url, "email")
    return data
