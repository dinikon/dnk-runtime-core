from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExportIssueResponse(BaseModel):
    """Передаёт диагностику публикации в последнем отчёте."""

    model_config = ConfigDict(from_attributes=True)

    publication_id: UUID
    severity: Literal["ERROR", "WARNING"]
    code: str
    message: str
    sku: str | None
    field_id: UUID | None
    rule_id: UUID | None
    path: tuple[str | int, ...]


class ListLatestFeedExportIssuesResponse(BaseModel):
    """Возвращает одну страницу диагностик."""

    items: tuple[ExportIssueResponse, ...]
    total: int
