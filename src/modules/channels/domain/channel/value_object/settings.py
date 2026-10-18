from dataclasses import dataclass
from urllib.parse import urlsplit
from src.modules.channels.domain.error import ChannelsValidationError


@dataclass(frozen=True, slots=True)
class ConnectionSettingsVO:
    """Хранит подтверждаемые параметры одного внешнего ресурса."""

    endpoint: str
    locales: tuple[str, ...]
    currency: str | None = None

    def __post_init__(self) -> None:
        """Отклоняет неоднозначные адреса и повторяющиеся языки."""
        try:
            parsed = urlsplit(self.endpoint)
            port = parsed.port
        except ValueError:
            raise ChannelsValidationError("invalid_endpoint") from None
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (port not in (None, 443))
        ):
            raise ChannelsValidationError("invalid_endpoint")
        if (
            not self.locales
            or len(self.locales) > 2
            or len(set(self.locales)) != len(self.locales)
        ):
            raise ChannelsValidationError("invalid_locales")
        if self.currency is not None and (
            len(self.currency) != 3 or not self.currency.isupper()
        ):
            raise ChannelsValidationError("invalid_currency")
        object.__setattr__(self, "endpoint", self.endpoint.rstrip("/"))
