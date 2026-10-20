from dataclasses import dataclass
from copy import deepcopy
import json
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from urllib.parse import urlsplit
from src.modules.channels.domain.error import ChannelsValidationError


@dataclass(frozen=True, slots=True)
class ConnectionSettingsVO:
    """Хранит подтверждаемые параметры одного внешнего ресурса."""

    endpoint: str
    options: dict[str, JsonValue]

    def __post_init__(self) -> None:
        """Проверяет HTTPS-адрес и ограниченный JSON-объект без правил конкретного плагина."""
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
        if not isinstance(self.options, dict):
            raise ChannelsValidationError("invalid_settings_shape")
        try:
            encoded = json.dumps(self.options, allow_nan=False)
        except (ValueError, TypeError, RecursionError):
            raise ChannelsValidationError("invalid_settings_shape") from None
        if len(encoded.encode()) > 65536:
            raise ChannelsValidationError("settings_too_large")
        object.__setattr__(self, "options", deepcopy(self.options))
        object.__setattr__(self, "endpoint", self.endpoint.rstrip("/"))
