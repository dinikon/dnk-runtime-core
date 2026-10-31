from uuid import UUID

from pydantic import BaseModel


class CreateChannelResponse(BaseModel):
    """HTTP-результат сценария CreateChannel."""

    id: UUID
    revision: int
    verification_job_id: UUID
