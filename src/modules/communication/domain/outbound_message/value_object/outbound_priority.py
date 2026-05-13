from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidOutboundPriorityError,
)


@dataclass(slots=True, frozen=True)
class OutboundPriorityVO:
    """Value object приоритета outbound message."""

    value: int

    def __post_init__(self) -> None:
        """Проверяет, что priority является неотрицательным целым числом."""
        if not isinstance(self.value, int) or self.value < 0:
            raise InvalidOutboundPriorityError()
