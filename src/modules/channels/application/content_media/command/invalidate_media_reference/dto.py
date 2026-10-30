from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InvalidateMediaReferenceResultDTO:
    """Новая pending ревизия после подтверждённой потери внешнего ID."""

    media_id: UUID
    revision: int
