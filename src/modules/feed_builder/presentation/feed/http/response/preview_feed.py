from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PreviewColumnResponse(BaseModel):
    """Передаёт название и ID экспортируемой колонки."""

    model_config = ConfigDict(from_attributes=True)
    field_id: UUID
    name: str


class PreviewIssueResponse(BaseModel):
    """Передаёт диагностику одной ячейки или позиции."""

    model_config = ConfigDict(from_attributes=True)
    field_id: UUID | None
    code: str
    message: str
    path: tuple[str | int, ...]
    rule_id: UUID | None


class PreviewRowResponse(BaseModel):
    """Передаёт вычисленные ячейки выбранной позиции."""

    model_config = ConfigDict(from_attributes=True)
    publication_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    sku: str | None
    values: tuple[str | None, ...]
    issues: tuple[PreviewIssueResponse, ...]
    readiness: str


class PreviewFeedResponse(BaseModel):
    """Передаёт версию, время расчёта и готовый образец фида."""

    feed_id: UUID
    version: int
    as_of: datetime
    total_enabled: int
    columns: tuple[PreviewColumnResponse, ...]
    rows: tuple[PreviewRowResponse, ...]
