from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResetPublicationOverrideCommand:
    """Передаёт намерение изменить ручное значение одного поля."""

    feed_id: UUID
    publication_id: UUID
    field_id: UUID
    expected_feed_version: int
    expected_version: int
