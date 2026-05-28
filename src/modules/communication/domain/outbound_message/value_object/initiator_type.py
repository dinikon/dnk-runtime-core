from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidInitiatorTypeError,
)

_ALLOWED_INITIATOR_TYPES = frozenset(
    {
        "CRM",
        "BROADCAST",
        "WORKFLOW",
        "CAMPAIGN",
        "API",
    }
)


@dataclass(slots=True, frozen=True)
class InitiatorTypeVO:
    """Value object типа инициатора communication request."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует initiator type и запрещает неизвестные значения."""
        if not isinstance(self.value, str):
            raise InvalidInitiatorTypeError()
        normalized = self.value.strip().upper()
        if not normalized or normalized not in _ALLOWED_INITIATOR_TYPES:
            raise InvalidInitiatorTypeError()
        object.__setattr__(self, "value", normalized)
