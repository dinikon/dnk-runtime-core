"""HTTP-ответ конкретного сценария Channels."""

from pydantic import BaseModel

from src.modules.channels.presentation.external_publication.http.response.fields import (
    PublicationCardFields,
)


class ListPublicationsResponse(BaseModel):
    """Не раскрывает документы хранения и данные доступа."""

    items: list[PublicationCardFields]
    total: int
    offset: int
    limit: int
    locale: str
    locales: list[str]
