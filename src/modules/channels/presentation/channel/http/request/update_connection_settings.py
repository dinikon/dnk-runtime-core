from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class UpdateConnectionSettingsRequest(BaseModel):
    """Принимает endpoint, полную конфигурацию плагина и отдельные секреты."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=1)
    endpoint: str = Field(max_length=2048)
    settings: dict[str, JsonValue]
    credentials: dict[str, str] | None = Field(default=None, repr=False)
