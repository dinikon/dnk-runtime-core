from dataclasses import dataclass

from src.modules.communication.domain.provider_connection.error import (
    InvalidProviderConnectionCodeError,
)


@dataclass(slots=True, frozen=True)
class ProviderConnectionCodeVO:
    """Value object tenant-local кода provider connection."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует код и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderConnectionCodeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderConnectionCodeError()
        object.__setattr__(self, "value", normalized)
