from dataclasses import dataclass
from src.modules.channels.application.content_feed.import_contracts import (
    FeedImportDetails,
)


@dataclass(frozen=True, slots=True)
class GetFeedImportResultDTO:
    """Публичное состояние и доступные действия без секретного документа."""

    operation: FeedImportDetails
