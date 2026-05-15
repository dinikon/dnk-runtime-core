from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderConnectorNameError,
)


@dataclass(slots=True, frozen=True)
class ProviderConnectorNameVO:
    """Value object имени provider connector."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует имя provider connector и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderConnectorNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderConnectorNameError()
        object.__setattr__(self, "value", normalized)
