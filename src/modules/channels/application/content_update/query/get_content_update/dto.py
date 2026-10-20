from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContentUpdateTextDTO:
    """Передаёт безопасные значения сравнения одной локали."""

    locale: str
    title: str | None
    body: str | None


@dataclass(frozen=True, slots=True)
class ContentUpdateItemDTO:
    """Проецирует одну позицию без native payload и секретов."""

    publication_id: UUID
    catalog_item_id: UUID
    external_id: str
    desired: tuple[ContentUpdateTextDTO, ...]
    observed: tuple[ContentUpdateTextDTO, ...]
    status: str
    issues: tuple[str, ...]
    attempts: int


@dataclass(frozen=True, slots=True)
class GetContentUpdateResultDTO:
    """Описывает страницу сравнения и прогресса исходящей операции."""

    id: UUID
    channel_id: UUID
    status: str
    revision: int
    sequence: int
    preview_hash: str | None
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None
    outbound_enabled: bool
    items: tuple[ContentUpdateItemDTO, ...]
    interrupted: bool = False
