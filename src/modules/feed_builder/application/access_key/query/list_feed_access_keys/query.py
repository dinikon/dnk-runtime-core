from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListFeedAccessKeysQuery:
    """Выбирает метаданные ключей конкретного фида."""

    feed_id: UUID
