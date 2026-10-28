from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UpdateCatalogBindingResponse(BaseModel):
    """Публичный результат update_catalog_binding."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
