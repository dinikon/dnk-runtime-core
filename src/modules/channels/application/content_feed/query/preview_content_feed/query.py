from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewContentFeedQuery:
    """Проверяет сохранённый источник без включения публичной выдачи."""

    channel_id: UUID
    feed_id: UUID
    actor_id: UUID
