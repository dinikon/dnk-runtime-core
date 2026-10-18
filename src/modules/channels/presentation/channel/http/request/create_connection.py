from pydantic import BaseModel, ConfigDict, Field


class CreateConnectionSettingsRequest(BaseModel):
    """Описывает полную замену параметров settings этого HTTP-сценария."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    endpoint: str = Field(max_length=2048)
    locales: tuple[str, ...] = Field(min_length=1, max_length=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class CreateConnectionRequest(BaseModel):
    """Принимает поля HTTP-сценария create_connection без tenant/actor из body."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=1)
    settings: CreateConnectionSettingsRequest
    credentials: dict[str, str] = Field(repr=False)
