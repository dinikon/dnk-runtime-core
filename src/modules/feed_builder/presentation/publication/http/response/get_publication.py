from pydantic import BaseModel
from src.modules.feed_builder.presentation.publication.http.response.list_publications import (
    PublicationListItemResponse,
)


class GetPublicationResponse(BaseModel):
    """Возвращает карточку публикации с текущим контекстом Feed."""

    publication: PublicationListItemResponse
    feed_version: int
    feed_status: str
