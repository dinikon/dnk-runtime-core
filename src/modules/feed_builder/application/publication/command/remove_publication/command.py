from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RemovePublicationCommand:
    """Передаёт намерение изменить участие существующей публикации."""

    feed_id: UUID
    publication_id: UUID
    expected_version: int
