from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)


@dataclass(frozen=True, slots=True)
class ChangePublicationStatusCommand:
    """Передаёт намерение изменить участие существующей публикации."""

    feed_id: UUID
    publication_id: UUID
    expected_version: int
    status: PublicationStatus
