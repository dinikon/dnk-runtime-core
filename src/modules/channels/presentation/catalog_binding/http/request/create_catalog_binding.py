from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.presentation.catalog_binding.http.request.fields import (
    PairRequest,
)


class CreateCatalogBindingRequest(BaseModel):
    """Вход конкретного сценария create_catalog_binding."""

    model_config = ConfigDict(extra="forbid")
    catalog_root_id: UUID
    mode: BindingMode
    publication_root_id: UUID | None = None
    items: list[PairRequest]
    catalog_token: str = Field(min_length=64, max_length=64)
    publication_token: str = Field(min_length=64, max_length=64)
    locale: str = Field(default="uk", min_length=2, max_length=35)
