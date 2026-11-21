from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class FieldLabelVO:
    """Пользовательская подпись поля."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует собственное строковое значение."""
        object.__setattr__(
            self,
            "value",
            text(self.value, label="FieldLabelVO", maximum=255, pattern=None),
        )
