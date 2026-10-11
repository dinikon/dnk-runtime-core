from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ValueOverride,
)


class PutCatalogItemContentRequest(BaseModel):
    """Отдельное тело команды put_catalog_item_content."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    expected_schema_version: int = Field(ge=1)
    values: dict[str, ValueOverride[str]]
