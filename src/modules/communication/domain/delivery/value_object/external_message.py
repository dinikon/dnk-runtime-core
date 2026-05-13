from __future__ import annotations

from dataclasses import dataclass

from src.modules.communication.domain.delivery.error import (
    InvalidExternalMessageIdError,
)


@dataclass(slots=True, frozen=True)
class ExternalMessageId:
    """Value object внешнего id сообщения provider."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует внешний id сообщения и запрещает пустое значение."""
        if not isinstance(self.value, str):
            raise InvalidExternalMessageIdError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidExternalMessageIdError()
        object.__setattr__(self, "value", normalized)


__all__ = ["ExternalMessageId"]
