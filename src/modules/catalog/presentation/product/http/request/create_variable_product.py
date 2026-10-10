from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CreateVariableProductVariantRequest(BaseModel):
    """Позиция полного редактора структуры в сценарии create_variable_product."""

    model_config = ConfigDict(extra="forbid")
    variant_id: UUID | None = None
    selection: dict[UUID, UUID] = Field(default_factory=dict)
    virtual: bool = False


class CreateVariableProductAxisRequest(BaseModel):
    """Ось со стабильными attribute/option ID."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int = Field(ge=0)


class CreateVariableProductVariableRequest(BaseModel):
    """Полная целевая структура VARIABLE; инварианты проверяет Product."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["variable"] = "variable"
    axes: tuple[CreateVariableProductAxisRequest, ...]
    default_selection: dict[UUID, UUID] | None = None
    variants: tuple[CreateVariableProductVariantRequest, ...]


class CreateVariableProductRequest(BaseModel):
    """Отдельное тело HTTP-сценария create_variable_product."""

    model_config = ConfigDict(extra="forbid")
    product_type_id: UUID | None = None
    structure: CreateVariableProductVariableRequest
