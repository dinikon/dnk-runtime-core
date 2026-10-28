from uuid import UUID
from pydantic import BaseModel


class CreateCatalogVariantResponse(BaseModel):
    """Идентичность новой позиции в указанном родителе."""

    id: UUID
    parent_id: UUID
