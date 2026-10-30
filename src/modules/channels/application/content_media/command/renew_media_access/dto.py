from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RenewMediaAccessResultDTO:
    """Результат renew_media_access без документов хранения."""

    media_id: UUID
    revision: int
    url: str = field(repr=False)
