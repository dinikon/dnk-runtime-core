from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class FeedVersionVO:
    """Хранит версию конкурентного сохранения, не ревизию схемы."""

    value: int

    def __post_init__(self) -> None:
        """Требует положительный BIGINT без неявного преобразования bool."""
        if type(self.value) is not int or not 1 <= self.value <= 9223372036854775807:
            raise InvalidFeedValueError("Версия Feed должна быть положительным BIGINT.")
