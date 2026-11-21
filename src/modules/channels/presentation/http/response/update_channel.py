from src.modules.channels.application.command.update_channel.dto import UpdateChannelDTO
from uuid import UUID

from pydantic import BaseModel


class UpdateChannelResponse(BaseModel):
    """HTTP-результат сценария UpdateChannel."""

    id: UUID
    revision: int
    verification_job_id: UUID

    @classmethod
    def from_dto(cls, value: UpdateChannelDTO) -> "UpdateChannelResponse":
        """Явно преобразует результат сценария в HTTP-ответ."""
        return cls(
            id=value.id,
            revision=value.revision,
            verification_job_id=value.verification_job_id,
        )
