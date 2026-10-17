from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.files import CatalogImageStream


@dataclass(frozen=True, slots=True)
class GetCatalogItemImageContentResultDTO:
    """Метаданные и управляемый поток назначенного изображения."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int
    stream: CatalogImageStream
