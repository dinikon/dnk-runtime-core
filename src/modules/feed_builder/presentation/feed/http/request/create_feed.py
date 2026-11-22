from pydantic import BaseModel, ConfigDict, Field
from src.modules.feed_builder.presentation.feed.http.schema.export_settings import (
    FeedExportSettingsSchema,
)


class CreateFeedRequest(BaseModel):
    """Принимает только общие настройки; схема и статус задаются Domain."""

    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=64)
    export_settings: FeedExportSettingsSchema
