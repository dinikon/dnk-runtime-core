from pydantic import BaseModel, ConfigDict, Field


class PutTagTranslationRequest(BaseModel):
    """Отдельное тело HTTP-сценария put_tag_translation."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=255)
