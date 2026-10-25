from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.catalog.application.catalog_import.contracts import (
    SourceField,
    SourceRecord,
)


@dataclass(frozen=True, slots=True)
class ImportSummaryDTO:
    """Проекция запуска для журнала и прогресса."""

    id: UUID
    source_name: str
    status: str
    version: int
    total: int
    processed: int
    created: int
    updated: int
    skipped: int
    errors: int
    warnings: int
    created_at: datetime
    finished_at: datetime | None
    error: str | None
    generation: int = 0
    can_resume: bool = False


@dataclass(frozen=True, slots=True)
class ImportAnalysisDTO:
    """Ограниченный предпросмотр; значения источника всегда остаются данными."""

    format: str = ""
    encoding: str | None = None
    delimiter: str | None = None
    record_path: str | None = None
    candidates: tuple[str, ...] = ()
    fields: tuple[SourceField, ...] = ()
    samples: tuple[SourceRecord, ...] = ()
    mapped_samples: tuple[dict[str, list[str]], ...] = ()
    warnings: tuple[str, ...] = ()
