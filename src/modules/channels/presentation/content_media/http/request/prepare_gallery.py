from pydantic import BaseModel, ConfigDict, Field


class PrepareGalleryRequest(BaseModel):
    """Фиксирует версии представления, состава и подключения."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)
    expected_binding_revision: int = Field(ge=1, strict=True)
    expected_config_revision: int = Field(ge=1, strict=True)
