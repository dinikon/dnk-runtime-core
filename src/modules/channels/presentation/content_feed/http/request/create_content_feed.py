from pydantic import BaseModel, ConfigDict, Field, SecretStr
from src.modules.channels.domain.types import JsonObject


class CreateContentFeedRequest(BaseModel):
    """Тело отдельного HTTP-сценария create_content_feed."""

    model_config = ConfigDict(extra="forbid")
    source_url: SecretStr = Field(min_length=1, max_length=8192)
    source_schema: str = "prom.yml.v1"
    source_settings: JsonObject = Field(default_factory=dict)
