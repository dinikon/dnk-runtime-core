from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SetProductAttributeValueRequest(BaseModel):
    """Общее enum-значение в сценарии set_product_attributes."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_id: UUID
    visible: bool = Field(strict=True)
    position: int = Field(ge=0, strict=True)


class SetProductAttributesRequest(BaseModel):
    """Полная замена attributes в отдельном HTTP-сценарии."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    values: tuple[SetProductAttributeValueRequest, ...]
