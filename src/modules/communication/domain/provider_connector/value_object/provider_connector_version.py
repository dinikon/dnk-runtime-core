from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderConnectorVersionError,
)


@dataclass(slots=True, frozen=True)
class ProviderConnectorVersionVO:
    """Value object версии provider connector."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует версию provider connector и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderConnectorVersionError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderConnectorVersionError()
        object.__setattr__(self, "value", normalized)
