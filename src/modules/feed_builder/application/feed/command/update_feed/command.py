from dataclasses import dataclass
from src.modules.feed_builder.application.feed.export_settings_dto import (
    FeedExportSettingsDTO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class UpdateFeedCommand:
    """Передаёт частичное изменение настроек с ожидаемой версией."""

    feed_id: FeedIdVO
    expected_version: int
    name: str | None = None
    code: str | None = None
    export_settings: FeedExportSettingsDTO | None = None
