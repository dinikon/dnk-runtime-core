"""Serialize bound Django fields without exposing passwords or executable HTML."""


def serialize_field(field):
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
