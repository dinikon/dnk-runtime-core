from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetFeedImportQuery:
    """Читает последнюю операцию текущего фида."""

    channel_id: UUID
    feed_id: UUID
