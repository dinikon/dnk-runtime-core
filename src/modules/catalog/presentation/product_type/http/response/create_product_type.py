from uuid import UUID
from pydantic import BaseModel


class CreateProductTypeResponse(BaseModel):
    """Ответ HTTP-сценария create_product_type."""

    id: UUID
    revision: int
    schema_version: int
