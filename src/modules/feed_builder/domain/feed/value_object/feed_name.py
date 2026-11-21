from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class FeedNameVO:
    """Название пользовательского Feed."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует собственное строковое значение."""
        object.__setattr__(
            self,
            "value",
            text(self.value, label="FeedNameVO", maximum=255, pattern=None),
        )
