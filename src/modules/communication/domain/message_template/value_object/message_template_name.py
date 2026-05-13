from dataclasses import dataclass

from src.modules.communication.domain.message_template.error import (
    InvalidMessageTemplateNameError,
)


@dataclass(slots=True, frozen=True)
class MessageTemplateNameVO:
    """Value object названия message template."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустое название шаблона."""
        if not isinstance(self.value, str):
            raise InvalidMessageTemplateNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidMessageTemplateNameError()
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Возвращает строковое название шаблона."""
        return self.value
