from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RevokeMediaAccessCommand:
    """Конкретное намерение revoke_media_access из доверенного контекста."""

    channel_id: UUID
    media_id: UUID
    expected_revision: int
