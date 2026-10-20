from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)


@dataclass(frozen=True, slots=True)
class PublicationImportImagePreviewDTO:
    """Передаёт результат конкретной фотографии для предпросмотра."""

    id: str
    file_id: UUID | None
    alt: str
    error_code: str | None


@dataclass(frozen=True, slots=True)
class GetPublicationImportResultDTO:
    """Описывает read-проекцию процесса без domain aggregate и внешних ссылок."""

    preparation_id: UUID
    publication_id: UUID
    actor_id: UUID
    status: str
    revision: int
    observed_revision: int
    created_at: datetime
    expires_at: datetime
    error_code: str | None
    values: CatalogDraftValuesDTO | None
    translations: dict[str, dict[str, str | None]]
    images: tuple[PublicationImportImagePreviewDTO, ...]
    warnings: tuple[str, ...]

    sequence: int = 0

    read_at: datetime | None = None
