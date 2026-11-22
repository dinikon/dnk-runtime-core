from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.feed_builder.application.feed.export_settings_dto import (
    FeedExportSettingsDTO,
)
from src.modules.feed_builder.application.feed.types import JsonObject


@dataclass(frozen=True, slots=True)
class UpdateFeedResultDTO:
    """Передаёт результат изменения настроек фида."""

    id: UUID
    name: str
    code: str
    status: str
    export_settings: FeedExportSettingsDTO
    schema: JsonObject
    version: int
    created_at: datetime
    updated_at: datetime
