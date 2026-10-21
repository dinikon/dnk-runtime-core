from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BatchExportSummaryDTO:
    """Показывает состояние пакета без приватного provider context и адреса фида."""

    id: UUID
    channel_id: UUID
    trigger: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_code: str | None
    counts: dict[str, int]
    interrupted: bool = False
    delivery_mode: str = "provider"


@dataclass(frozen=True, slots=True)
class BatchExportItemDTO:
    """Показывает результат исходной публикации без технического снимка."""

    publication_id: UUID
    catalog_item_id: UUID
    external_id: str
    status: str
    issues: tuple[str, ...]
    titles: dict[str, str]
