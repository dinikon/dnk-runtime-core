from django import template

register = template.Library()


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
    return {
        "form": form,
        "fields": [field for field in form.visible_fields() if field.name != exclude],
    }


@register.inclusion_tag("accounts/ui/field.html")
def core_field(field):
    return {"field": field}


@register.filter
def field_schema(field):
    """JSON data, never executable markup. Passwords remain exclusively in DOM."""
    from django.utils.html import strip_tags

    widget = field.field.widget
    attrs = field.build_widget_attrs(widget.attrs.copy())
    kind = getattr(widget, "input_type", "text")
    if widget.__class__.__name__ == "Textarea":
        kind = "textarea"
    if widget.__class__.__name__ in {"Select", "RadioSelect"}:
        kind = "radio-group" if widget.__class__.__name__ == "RadioSelect" else "select"
    attrs = {
        key: value
        for key, value in attrs.items()
        if key
        in {
            "autocomplete",
            "inputmode",
            "placeholder",
            "minlength",
            "maxlength",
            "min",
            "max",
            "step",
            "pattern",
            "rows",
            "readonly",
            "disabled",
            "required",
            "autofocus",
        }
    }
    attrs.update({"id": field.auto_id, "name": field.html_name})
    value = "" if kind == "password" else field.value()
    if value is None:
        value = ""
    return {
        "type": kind,
        "attrs": attrs,
        "label": str(field.label or field.name),
        "value": (
            value if isinstance(value, (str, bool, int, float, list)) else str(value)
        ),
        "help": strip_tags(str(field.help_text)),
        "errors": [str(error) for error in field.errors],
        "options": (
            [
                {"value": str(value), "label": str(label)}
                for value, label in getattr(widget, "choices", [])
            ]
            if kind in {"select", "radio-group"}
            else []
        ),
    }


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
