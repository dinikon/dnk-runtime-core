from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InvalidateMediaReferenceCommand:
    """Подтверждённое исполнителем исчезновение attachment, не автоматический retry."""

    channel_id: UUID
    media_id: UUID
    expected_revision: int
