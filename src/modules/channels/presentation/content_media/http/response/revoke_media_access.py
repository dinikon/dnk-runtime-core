from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_media.command.revoke_media_access.dto import (
    RevokeMediaAccessResultDTO,
)


class RevokeMediaAccessResponse(BaseModel):
    """Публичный результат revoke_media_access без технических полей media."""

    media_id: UUID
    revision: int

    @classmethod
    def from_dto(
        cls, result: RevokeMediaAccessResultDTO
    ) -> "RevokeMediaAccessResponse":
        """Перечисляет разрешённые поля явно."""
        return cls(media_id=result.media_id, revision=result.revision)
