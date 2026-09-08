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
