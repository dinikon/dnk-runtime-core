from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IssuedFeedAccessKeyDTO:
    """Возвращает секрет только в ответе на выпуск."""

    id: UUID
    name: str
    created_at: datetime
    expires_at: datetime | None
    token: str = field(repr=False)
