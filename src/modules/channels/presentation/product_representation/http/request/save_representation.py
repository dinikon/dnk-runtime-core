from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.presentation.product_representation.http.request.fields import (
    RepresentationOverridesRequest,
)


class SaveRepresentationRequest(BaseModel):
    """Явный контракт save_representation с проверкой всех ревизий редактора."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    expected_binding_revision: int = Field(ge=1, strict=True)
    expected_config_revision: int = Field(ge=1, strict=True)
    overrides: RepresentationOverridesRequest
