from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ChangeProductTypeRequest(BaseModel):
    """Тело HTTP-сценария change_product_type; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    product_type_id: UUID
