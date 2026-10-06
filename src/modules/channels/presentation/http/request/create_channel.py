from pydantic import BaseModel, ConfigDict, Field


class CreateChannelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=255)
    kind: str
    config_version: int = Field(ge=1)
    connection_settings: dict[str, str] = Field(repr=False)
    is_active: bool = True
