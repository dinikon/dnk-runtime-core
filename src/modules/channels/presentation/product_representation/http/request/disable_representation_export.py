from pydantic import BaseModel, ConfigDict, Field


class DisableRepresentationExportRequest(BaseModel):
    """Явный контракт disable_representation_export с проверкой всех ревизий редактора."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    expected_binding_revision: int = Field(ge=1, strict=True)
    expected_config_revision: int = Field(ge=1, strict=True)
