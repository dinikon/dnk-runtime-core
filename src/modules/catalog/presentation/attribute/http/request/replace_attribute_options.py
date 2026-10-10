from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ReplaceAttributeOptionsOptionRequest(BaseModel):
    """Значение enum в конкретном HTTP-сценарии replace_attribute_options."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    option_id: UUID | None = None


class ReplaceAttributeOptionsRequest(BaseModel):
    """Отдельное тело HTTP-сценария replace_attribute_options."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    options: tuple[ReplaceAttributeOptionsOptionRequest, ...]
