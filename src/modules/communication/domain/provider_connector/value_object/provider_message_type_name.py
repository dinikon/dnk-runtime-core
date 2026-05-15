from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderMessageTypeNameError,
)


@dataclass(slots=True, frozen=True)
class ProviderMessageTypeNameVO:
    """Value object имени provider message type."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует имя provider message type и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderMessageTypeNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderMessageTypeNameError()
        object.__setattr__(self, "value", normalized)
