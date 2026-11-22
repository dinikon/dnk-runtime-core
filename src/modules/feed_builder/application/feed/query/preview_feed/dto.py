from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewColumnDTO:
    """Описывает экспортируемую колонку в порядке схемы."""

    field_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class PreviewIssueDTO:
    """Привязывает диагностику к ячейке, правилу или целой позиции."""

    field_id: UUID | None
    code: str
    message: str
    path: tuple[str | int, ...]
    rule_id: UUID | None


@dataclass(frozen=True, slots=True)
class PreviewRowDTO:
    """Содержит итоговые значения и диагностику одной позиции предпросмотра."""

    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    values: tuple[str | None, ...]
    issues: tuple[PreviewIssueDTO, ...]
    readiness: str


@dataclass(frozen=True, slots=True)
class PreviewFeedResultDTO:
    """Передаёт образец с количеством всех включённых публикаций."""

    feed_id: UUID
    version: int
    as_of: datetime
    total_enabled: int
    columns: tuple[PreviewColumnDTO, ...]
    rows: tuple[PreviewRowDTO, ...]
