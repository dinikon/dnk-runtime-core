import ipaddress
from urllib.parse import urlsplit, urlunsplit

from src.modules.channels.application.error import ChannelInputError


def normalize_endpoint(value: str) -> str:
    """Нормализует публичный HTTPS base URL, сохраняя подпуть WordPress."""
    try:
        url = urlsplit(value.strip())
        host = (url.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        port = url.port
        if (
            url.scheme != "https"
            or not host
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or "\\" in value
            or "%" in host
        ):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if host == "localhost" or host.endswith(".localhost") or "." not in host:
                raise ValueError
        else:
            if not address.is_global:
                raise ValueError
        authority = f"[{host}]" if ":" in host else host
        if port and port != 443:
            authority += f":{port}"
        return urlunsplit(("https", authority, url.path.rstrip("/"), "", ""))
    except (ValueError, UnicodeError):
        raise ChannelInputError("endpoint_invalid", field="config.endpoint") from None
