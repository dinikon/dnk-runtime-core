from dataclasses import dataclass

from src.modules.communication.domain.outbound_message.error import (
    InvalidIdempotencyKeyError,
)


@dataclass(slots=True, frozen=True)
class IdempotencyKeyVO:
    """Value object ключа идемпотентности communication send."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует idempotency key и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidIdempotencyKeyError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidIdempotencyKeyError()
        object.__setattr__(self, "value", normalized)
