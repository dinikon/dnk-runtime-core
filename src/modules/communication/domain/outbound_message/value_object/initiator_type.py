from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidInitiatorTypeError,
)


@dataclass(slots=True, frozen=True)
class InitiatorTypeVO:
    """Value object типа инициатора communication request."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует initiator type и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidInitiatorTypeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidInitiatorTypeError()
        object.__setattr__(self, "value", normalized)
