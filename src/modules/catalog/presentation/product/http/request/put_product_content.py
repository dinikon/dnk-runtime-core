from pydantic import BaseModel, ConfigDict


class PutProductContentRequest(BaseModel):
    """Полная замена одного перевода без изменения других локалей."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    description: str | None = None
