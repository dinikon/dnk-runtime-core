from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.communication.domain.message_template.error import (
    InvalidTemplateVersionTimestampError,
)


@dataclass(slots=True, frozen=True)
class TemplateVersionTimestampVO:
    """Value object UTC timestamp версии шаблона."""

    value: datetime

    def __post_init__(self) -> None:
        """Нормализует timestamp версии в UTC с точностью до секунд."""
        if not isinstance(self.value, datetime):
            raise InvalidTemplateVersionTimestampError()
        normalized = self.value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=UTC)
        normalized = normalized.astimezone(UTC).replace(microsecond=0)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Возвращает ISO-представление версии."""
        return self.value.isoformat()
