from pydantic import BaseModel, ConfigDict, Field


class CreateChannelRequest(BaseModel):
    """Ограничивает входные поля HTTP-сценария create_channel; credentials скрыты из repr."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    name: str
    kind: str
    config_version: int = Field(ge=1)
    connection_settings: dict[str, str] = Field(repr=False)
    is_active: bool = True
