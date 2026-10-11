from pydantic import BaseModel, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    SchemaResponse,
)


class GetDefaultProductTypeResponse(BaseModel):
    """Read-only HTTP контракт Default."""

    content_schema: SchemaResponse = Field(alias="schema")
    locale: str
