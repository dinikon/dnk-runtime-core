from uuid import UUID
from pydantic import BaseModel, ConfigDict
from src.modules.channels.presentation.catalog_binding.http.response.fields import (
    PositionFields,
)


class ListCatalogBindingCandidatesResponse(BaseModel):
    """Публичный результат list_catalog_binding_candidates."""

    model_config = ConfigDict(from_attributes=True)
    items: list[PositionFields]
    occupied_ids: list[UUID]
    total: int
    offset: int
    limit: int
