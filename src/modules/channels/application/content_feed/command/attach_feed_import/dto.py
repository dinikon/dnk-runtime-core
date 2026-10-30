from dataclasses import dataclass
from src.modules.channels.application.content_feed.import_contracts import (
    FeedImportDetails,
)


@dataclass(frozen=True, slots=True)
class AttachFeedImportResultDTO:
    """Публичный результат сценария attach_feed_import."""

    operation: FeedImportDetails
