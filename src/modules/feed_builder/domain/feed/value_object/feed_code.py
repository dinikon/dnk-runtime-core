from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.validation import text


@dataclass(frozen=True, slots=True)
class FeedCodeVO:
    """Стабильный код Feed без проверки уникальности в tenant."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет и нормализует собственное строковое значение."""
        object.__setattr__(
            self,
            "value",
            text(
                self.value, label="FeedCodeVO", maximum=64, pattern="[a-z][a-z0-9_-]*"
            ),
        )
