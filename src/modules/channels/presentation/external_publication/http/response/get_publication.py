"""HTTP-ответ конкретного сценария Channels."""

from pydantic import BaseModel

from src.modules.channels.presentation.external_publication.http.response.fields import (
    PublicationCardFields,
)


class GetPublicationResponse(BaseModel):
    """Не раскрывает документы хранения и данные доступа."""

    card: PublicationCardFields
    locale: str
    locales: list[str]
