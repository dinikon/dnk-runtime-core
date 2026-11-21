from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class FieldKeyVO:
    """Внутренний ключ равноправного пользовательского поля."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует собственное строковое значение."""
        object.__setattr__(
            self,
            "value",
            text(
                self.value,
                label="FieldKeyVO",
                maximum=64,
                pattern="[A-Za-z_][A-Za-z0-9_]*",
            ),
        )
