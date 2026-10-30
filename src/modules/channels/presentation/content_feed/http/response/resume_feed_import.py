from pydantic import BaseModel
from src.modules.channels.application.content_feed.command.resume_feed_import.dto import (
    ResumeFeedImportResultDTO,
)
from src.modules.channels.presentation.content_feed.http.response.import_fields import (
    FeedImportFields,
)


class ResumeFeedImportResponse(BaseModel):
    """Ответ конкретного сценария resume_feed_import."""

    operation: FeedImportFields

    @classmethod
    def from_dto(cls, value: ResumeFeedImportResultDTO) -> "ResumeFeedImportResponse":
        """Явно переносит публичные поля состояния."""
        return cls(operation=FeedImportFields.from_details(value.operation))
