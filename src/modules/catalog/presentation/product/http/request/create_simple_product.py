from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CreateSimpleProductRequest(BaseModel):
    """Тело HTTP-сценария create_simple_product; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    product_type_id: UUID | None = None
    virtual: bool = False
