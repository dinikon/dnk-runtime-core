from uuid import UUID
from pydantic import BaseModel


class BindExistingPublicationResponse(BaseModel):
    """Возвращает стабильные идентификаторы и новую версию представления."""

    catalog_item_id: UUID
    representation_id: UUID
    binding_id: UUID
    revision: int
