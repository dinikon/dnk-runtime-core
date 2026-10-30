from pydantic import BaseModel, ConfigDict, Field, SecretStr
from src.modules.channels.domain.types import JsonObject


class ChangeContentFeedSourceRequest(BaseModel):
    """Тело отдельного HTTP-сценария change_content_feed_source."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
    source_url: SecretStr | None = Field(default=None, min_length=1, max_length=8192)
    source_schema: str = "prom.yml.v1"
    source_settings: JsonObject = Field(default_factory=dict)
