from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_media.command.renew_media_access.dto import (
    RenewMediaAccessResultDTO,
)


class RenewMediaAccessResponse(BaseModel):
    """Публичный результат renew_media_access без технических полей media."""

    media_id: UUID
    revision: int
    url: str

    @classmethod
    def from_dto(cls, result: RenewMediaAccessResultDTO) -> "RenewMediaAccessResponse":
        """Перечисляет разрешённые поля явно."""
        return cls(media_id=result.media_id, revision=result.revision, url=result.url)
