from dataclasses import dataclass
from src.modules.feed_builder.application.feed.export_settings_dto import (
    FeedExportSettingsDTO,
)


@dataclass(frozen=True, slots=True)
class CreateFeedCommand:
    """Передаёт настройки нового фида без схемы, статуса или клиентского ID."""

    name: str
    code: str
    export_settings: FeedExportSettingsDTO
