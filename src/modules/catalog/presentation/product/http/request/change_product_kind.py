from uuid import UUID
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field


class ChangeProductKindVariantRequest(BaseModel):
    """Позиция полного редактора структуры в сценарии change_product_kind."""

    model_config = ConfigDict(extra="forbid")
    variant_id: UUID | None = None
    selection: dict[UUID, UUID] = Field(default_factory=dict)
    virtual: bool = False


class ChangeProductKindAxisRequest(BaseModel):
    """Ось со стабильными attribute/option ID."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int = Field(ge=0)


class ChangeProductKindVariableRequest(BaseModel):
    """Полная целевая структура VARIABLE; инварианты проверяет Product."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["variable"] = "variable"
    axes: tuple[ChangeProductKindAxisRequest, ...]
    default_selection: dict[UUID, UUID] | None = None
    variants: tuple[ChangeProductKindVariantRequest, ...]


class ChangeProductKindSimpleRequest(BaseModel):
    """Полная целевая структура SIMPLE с одной явно выбранной позицией."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["simple"]
    variant: ChangeProductKindVariantRequest


class ChangeProductKindRequest(BaseModel):
    """Отдельное тело HTTP-сценария change_product_kind."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    structure: Annotated[
        ChangeProductKindSimpleRequest | ChangeProductKindVariableRequest,
        Field(discriminator="kind"),
    ]
