from uuid import UUID
from pydantic import BaseModel


class CreateCatalogItemFromPublicationResponse(BaseModel):
    """Возвращает сохранённый результат атомарного create+bind."""

    catalog_item_id: UUID
    representation_id: UUID
    binding_id: UUID
