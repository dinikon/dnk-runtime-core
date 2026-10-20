from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationImportImageQuery:
    """Читает фото только из конкретного доступного пользователю предпросмотра."""

    tenant_id: UUID
    actor_id: UUID
    preparation_id: UUID
    image_id: str
