from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CreateCatalogBindingResponse(BaseModel):
    """Публичный результат create_catalog_binding."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
