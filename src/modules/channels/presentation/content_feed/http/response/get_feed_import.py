from pydantic import BaseModel
from src.modules.channels.application.content_feed.query.get_feed_import.dto import (
    GetFeedImportResultDTO,
)
from src.modules.channels.presentation.content_feed.http.response.import_fields import (
    FeedImportFields,
)


class GetFeedImportResponse(BaseModel):
    """Отдельный HTTP-ответ чтения операции."""

    operation: FeedImportFields

    @classmethod
    def from_dto(cls, value: GetFeedImportResultDTO) -> "GetFeedImportResponse":
        """Явно переносит разрешённые поля."""
        return cls(operation=FeedImportFields.from_details(value.operation))
