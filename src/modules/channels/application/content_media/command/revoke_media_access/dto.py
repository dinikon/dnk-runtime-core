from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RevokeMediaAccessResultDTO:
    """Результат revoke_media_access без документов хранения."""

    media_id: UUID
    revision: int
