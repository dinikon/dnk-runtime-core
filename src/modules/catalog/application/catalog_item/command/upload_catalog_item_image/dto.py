from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UploadCatalogItemImageResultDTO:
    """Назначенное изображение и подтверждённые ревизии семьи."""

    item_id: UUID
    root_id: UUID
    image_id: UUID
    file_id: UUID
    revision: int
    root_revision: int
