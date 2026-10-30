from pydantic import BaseModel, ConfigDict, Field


class PreviewRepresentationRequest(BaseModel):
    """Позволяет выбрать подмножество настроенных локалей; по умолчанию читает все."""

    model_config = ConfigDict(extra="forbid")

    locales: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=20)
