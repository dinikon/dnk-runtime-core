from pydantic import BaseModel
from src.modules.channels.application.content_feed.command.attach_feed_import.dto import (
    AttachFeedImportResultDTO,
)
from src.modules.channels.presentation.content_feed.http.response.import_fields import (
    FeedImportFields,
)


class AttachFeedImportResponse(BaseModel):
    """Ответ конкретного сценария attach_feed_import."""

    operation: FeedImportFields

    @classmethod
    def from_dto(cls, value: AttachFeedImportResultDTO) -> "AttachFeedImportResponse":
        """Явно переносит публичные поля состояния."""
        return cls(operation=FeedImportFields.from_details(value.operation))
