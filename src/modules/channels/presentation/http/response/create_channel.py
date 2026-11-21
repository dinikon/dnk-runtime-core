from src.modules.channels.application.command.create_channel.dto import CreateChannelDTO
from uuid import UUID

from pydantic import BaseModel


class CreateChannelResponse(BaseModel):
    """HTTP-результат сценария CreateChannel."""

    id: UUID
    revision: int
    verification_job_id: UUID

    @classmethod
    def from_dto(cls, value: CreateChannelDTO) -> "CreateChannelResponse":
        """Явно преобразует результат сценария в HTTP-ответ."""
        return cls(
            id=value.id,
            revision=value.revision,
            verification_job_id=value.verification_job_id,
        )
