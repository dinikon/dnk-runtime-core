from pydantic import BaseModel, ConfigDict
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    StructureValue,
)


class CreateVariableCatalogItemRequest(BaseModel):
    """Отдельное тело команды create_variable_catalog_item."""

    model_config = ConfigDict(extra="forbid")
    structure: StructureValue
