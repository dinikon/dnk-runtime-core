from pydantic import BaseModel
from src.modules.channels.application.content_feed.command.resolve_feed_import.dto import (
    ResolveFeedImportResultDTO,
)
from src.modules.channels.presentation.content_feed.http.response.import_fields import (
    FeedImportFields,
)


class ResolveFeedImportResponse(BaseModel):
    """Ответ конкретного сценария resolve_feed_import."""

    operation: FeedImportFields

    @classmethod
    def from_dto(cls, value: ResolveFeedImportResultDTO) -> "ResolveFeedImportResponse":
        """Явно переносит публичные поля состояния."""
        return cls(operation=FeedImportFields.from_details(value.operation))
