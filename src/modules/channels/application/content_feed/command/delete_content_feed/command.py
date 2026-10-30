from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeleteContentFeedCommand:
    """Намерение удалить конкретную ревизию фида текущего канала."""

    channel_id: UUID
    feed_id: UUID
    expected_revision: int
