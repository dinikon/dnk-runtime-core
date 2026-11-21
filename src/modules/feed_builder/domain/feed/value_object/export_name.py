from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class ExportNameVO:
    """Безопасное имя колонки или XML-элемента без namespace."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует собственное строковое значение."""
        object.__setattr__(
            self,
            "value",
            text(
                self.value,
                label="ExportNameVO",
                maximum=128,
                pattern="[A-Za-z_][A-Za-z0-9_.-]*",
            ),
        )
