from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Literal
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    StructureValue,
)


class ChangeCatalogItemKindRequest(BaseModel):
    """Отдельное тело команды change_catalog_item_kind."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    kind: Literal["simple", "variable"]
    structure: StructureValue | None = None
    selected_item_id: UUID | None = None
    discarded_ids: tuple[UUID, ...] = ()
    carry_to_index: int | None = Field(default=None, ge=0)
