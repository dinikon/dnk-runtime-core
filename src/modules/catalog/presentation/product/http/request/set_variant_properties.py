from pydantic import BaseModel, ConfigDict, Field


class SetVariantPropertiesRequest(BaseModel):
    """Тело HTTP-сценария set_variant_properties; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    virtual: bool
    downloadable: bool
