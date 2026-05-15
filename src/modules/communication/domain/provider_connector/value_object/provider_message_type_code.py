from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderMessageTypeCodeError,
)


@dataclass(slots=True, frozen=True)
class ProviderMessageTypeCodeVO:
    """Value object кода provider message type."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует код provider message type и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderMessageTypeCodeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderMessageTypeCodeError()
        object.__setattr__(self, "value", normalized)
