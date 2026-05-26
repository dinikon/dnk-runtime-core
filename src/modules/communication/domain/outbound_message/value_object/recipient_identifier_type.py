from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidRecipientIdentifierTypeError,
)


@dataclass(slots=True, frozen=True)
class RecipientIdentifierTypeVO:
    """Value object generic recipient identifier type."""

    value: str

    def __post_init__(self) -> None:
        """Normalize recipient identifier type and reject blank values."""
        if not isinstance(self.value, str):
            raise InvalidRecipientIdentifierTypeError()
        normalized = self.value.strip().upper()
        if not normalized:
            raise InvalidRecipientIdentifierTypeError()
        object.__setattr__(self, "value", normalized)
