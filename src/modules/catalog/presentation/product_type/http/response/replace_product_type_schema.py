from uuid import UUID
from pydantic import BaseModel


class ReplaceProductTypeSchemaResponse(BaseModel):
    """Ответ HTTP-сценария replace_product_type_schema."""

    id: UUID
    revision: int
    schema_version: int
