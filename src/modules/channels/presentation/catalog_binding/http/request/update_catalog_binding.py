from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.presentation.catalog_binding.http.request.fields import (
    PairRequest,
)


class UpdateCatalogBindingRequest(BaseModel):
    """Вход конкретного сценария update_catalog_binding."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)
    items: list[PairRequest]
    catalog_token: str = Field(min_length=64, max_length=64)
    publication_token: str = Field(min_length=64, max_length=64)
    locale: str = Field(default="uk", min_length=2, max_length=35)
