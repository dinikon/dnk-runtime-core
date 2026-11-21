from src.modules.channels.application.command.verify_connection.dto import (
    VerifyConnectionDTO,
)
from uuid import UUID

from pydantic import BaseModel


class VerifyConnectionResponse(BaseModel):
    """HTTP-результат сценария VerifyConnection."""

    id: UUID
    revision: int
    verification_job_id: UUID

    @classmethod
    def from_dto(cls, value: VerifyConnectionDTO) -> "VerifyConnectionResponse":
        """Явно преобразует результат сценария в HTTP-ответ."""
        return cls(
            id=value.id,
            revision=value.revision,
            verification_job_id=value.verification_job_id,
        )
