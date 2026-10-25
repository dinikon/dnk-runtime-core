from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CatalogImportSummaryResponse(BaseModel):
    """Публичное состояние запуска без приватных координат источника."""

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
    generation: int
    can_resume: bool


class ImportMappingResponse(BaseModel):
    """Подтверждённая связь поля и источника."""

    target: str
    source: str | None
    constant: str | None
    locale: str | None


class ImportConfigurationResponse(BaseModel):
    """Настройки предпросмотра и будущего запуска."""

    mappings: list[ImportMappingResponse]
    mode: str
    clear_empty: bool
    default_locale: str
    timezone: str
    encoding: str | None
    delimiter: str | None
    record_path: str | None


class ImportSourceFieldResponse(BaseModel):
    """Стабильный ID столбца или пути XML."""

    id: str
    label: str


class ImportSourceSampleResponse(BaseModel):
    """Ограниченные текстовые значения записи."""

    number: int
    values: dict[str, list[str]]


class ImportAnalysisResponse(BaseModel):
    """Параметры распознанного источника и первые записи."""

    format: str
    encoding: str | None
    delimiter: str | None
    record_path: str | None
    candidates: list[str]
    fields: list[ImportSourceFieldResponse]
    samples: list[ImportSourceSampleResponse]
    mapped_samples: list[dict[str, list[str]]]
    warnings: list[str]


class GetCatalogImportResponse(BaseModel):
    """HTTP-детали конкретного импорта."""

    run: CatalogImportSummaryResponse
    configuration: ImportConfigurationResponse
    analysis: ImportAnalysisResponse
