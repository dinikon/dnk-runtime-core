from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderChannelCodeError,
)


@dataclass(slots=True, frozen=True)
class ProviderChannelCodeVO:
    """Value object кода канала provider connector."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует код канала и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderChannelCodeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderChannelCodeError()
        object.__setattr__(self, "value", normalized)
