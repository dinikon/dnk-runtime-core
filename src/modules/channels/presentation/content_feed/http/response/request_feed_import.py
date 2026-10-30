from pydantic import BaseModel
from src.modules.channels.application.content_feed.command.request_feed_import.dto import (
    RequestFeedImportResultDTO,
)
from src.modules.channels.presentation.content_feed.http.response.import_fields import (
    FeedImportFields,
)


class RequestFeedImportResponse(BaseModel):
    """Ответ конкретного сценария request_feed_import."""

    operation: FeedImportFields

    @classmethod
    def from_dto(cls, value: RequestFeedImportResultDTO) -> "RequestFeedImportResponse":
        """Явно переносит публичные поля состояния."""
        return cls(operation=FeedImportFields.from_details(value.operation))
