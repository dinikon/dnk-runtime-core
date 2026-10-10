from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ReplaceVariantsVariantRequest(BaseModel):
    """Позиция полного редактора структуры в сценарии replace_variants."""

    model_config = ConfigDict(extra="forbid")
    variant_id: UUID | None = None
    selection: dict[UUID, UUID] = Field(default_factory=dict)
    virtual: bool = False


class ReplaceVariantsAxisRequest(BaseModel):
    """Ось со стабильными attribute/option ID."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int = Field(ge=0)


class ReplaceVariantsVariableRequest(BaseModel):
    """Полная целевая структура VARIABLE; инварианты проверяет Product."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["variable"] = "variable"
    axes: tuple[ReplaceVariantsAxisRequest, ...]
    default_selection: dict[UUID, UUID] | None = None
    variants: tuple[ReplaceVariantsVariantRequest, ...]


class ReplaceVariantsRequest(BaseModel):
    """Отдельное тело HTTP-сценария replace_variants."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    structure: ReplaceVariantsVariableRequest
