from pydantic import BaseModel, ConfigDict, Field


class CreateChannelRequest(BaseModel):
    """Принимает поля HTTP-сценария create_channel без tenant/actor из body."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=200)
    platform_kind: str = Field(min_length=1, max_length=80)
