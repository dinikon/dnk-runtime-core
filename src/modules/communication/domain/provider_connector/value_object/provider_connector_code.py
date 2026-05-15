from dataclasses import dataclass

from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderConnectorCodeError,
)


@dataclass(slots=True, frozen=True)
class ProviderConnectorCodeVO:
    """Value object кода provider connector."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует код provider connector и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidProviderConnectorCodeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProviderConnectorCodeError()
        object.__setattr__(self, "value", normalized)
