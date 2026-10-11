from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    StructureValue,
)


class ReplaceCatalogItemStructureRequest(BaseModel):
    """Отдельное тело команды replace_catalog_item_structure."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    structure: StructureValue
    removed_ids: tuple[UUID, ...] = ()
