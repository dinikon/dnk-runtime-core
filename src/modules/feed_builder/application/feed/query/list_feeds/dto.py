from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FeedListItemDTO:
    """Передаёт строку списка без полного JSON-определения схемы."""

    id: UUID
    name: str
    code: str
    status: str
    format: str
    fields_count: int
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ListFeedsResultDTO:
    """Передаёт страницу списка вместе с общим количеством."""

    items: tuple[FeedListItemDTO, ...]
    total: int
    limit: int
    offset: int
