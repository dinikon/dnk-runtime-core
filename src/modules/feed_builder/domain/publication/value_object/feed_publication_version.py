from dataclasses import dataclass
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)


@dataclass(frozen=True, slots=True)
class FeedPublicationVersionVO:
    """Хранит положительную BIGINT-версию сохранения публикации."""

    value: int

    def __post_init__(self) -> None:
        """Не допускает bool, переполнение и неявное преобразование строки."""
        if type(self.value) is not int or not 1 <= self.value <= 9223372036854775807:
            raise InvalidPublicationValueError(
                "Версия публикации должна быть положительным BIGINT."
            )
