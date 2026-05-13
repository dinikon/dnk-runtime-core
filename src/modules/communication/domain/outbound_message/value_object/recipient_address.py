from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidRecipientAddressError,
)


@dataclass(slots=True, frozen=True)
class RecipientAddressVO:
    """Value object адреса получателя outbound message."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует адрес получателя и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidRecipientAddressError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidRecipientAddressError()
        object.__setattr__(self, "value", normalized)
