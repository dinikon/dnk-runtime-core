import re
from urllib.parse import urlsplit, urlunsplit
from src.modules.channels.application.plugin_contract import ProviderJsonValue


def original_image_url(value: ProviderJsonValue) -> ProviderJsonValue:
    """Убирает размер CDN Prom, сохраняя неизвестные URL для общей проверки галереи."""
    if not isinstance(value, str):
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if (
        parsed.scheme != "https"
        or parsed.netloc != "images.prom.ua"
        or parsed.query
        or parsed.fragment
    ):
        return value
    match = re.fullmatch(r"(/\d+)_w[1-9]\d*_h[1-9]\d*(_[^/]+)", parsed.path)
    if match is None:
        return value
    return urlunsplit(parsed._replace(path=match[1] + match[2]))
