from dataclasses import dataclass

from src.modules.communication.domain.message_template.error import (
    InvalidMessageTemplateCodeError,
)


@dataclass(slots=True, frozen=True)
class MessageTemplateCodeVO:
    """Value object кода message template."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустой код шаблона."""
        if not isinstance(self.value, str):
            raise InvalidMessageTemplateCodeError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidMessageTemplateCodeError()
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Возвращает строковый код шаблона."""
        return self.value
