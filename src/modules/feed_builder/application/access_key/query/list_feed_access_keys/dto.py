from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

type FeedAccessKeyViewStatus = Literal["ACTIVE", "EXPIRED", "REVOKED"]


@dataclass(frozen=True, slots=True)
class FeedAccessKeyListItemDTO:
    """Показывает метаданные ключа без digest или секрета."""

    id: UUID
    name: str
    status: FeedAccessKeyViewStatus
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class ListFeedAccessKeysDTO:
    """Возвращает известные ключи, включая уже отозванные."""

    items: tuple[FeedAccessKeyListItemDTO, ...]
