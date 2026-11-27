from dataclasses import dataclass

from src.modules.feed_builder.domain.access_key.error import InvalidAccessKeyValueError


@dataclass(frozen=True, slots=True)
class AccessKeyNameVO:
    """Хранит краткое название интеграции владельца токена."""

    value: str

    def __post_init__(self) -> None:
        """Убирает внешние пробелы и проверяет отображаемое название."""
        if not isinstance(self.value, str):
            raise InvalidAccessKeyValueError("Название токена должно быть строкой.")
        value = self.value.strip()
        if not 1 <= len(value) <= 120 or not value.isprintable():
            raise InvalidAccessKeyValueError(
                "Введите название токена от 1 до 120 символов."
            )
        object.__setattr__(self, "value", value)
