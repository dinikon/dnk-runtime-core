from dataclasses import dataclass

from src.modules.communication.domain.provider_connection.error import (
    InvalidProviderConnectionNameError,
)


@dataclass(slots=True, frozen=True)
class ProviderConnectionNameVO:
    """Value object названия provider connection."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует название и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderConnectionNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderConnectionNameError()
        object.__setattr__(self, "value", normalized)
