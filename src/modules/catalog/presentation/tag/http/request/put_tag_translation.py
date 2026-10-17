from pydantic import BaseModel, ConfigDict, Field


class PutTagTranslationRequest(BaseModel):
    """Отдельное тело HTTP-сценария put_tag_translation."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=255)
