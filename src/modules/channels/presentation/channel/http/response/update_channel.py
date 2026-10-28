from uuid import UUID

from pydantic import BaseModel


class UpdateChannelResponse(BaseModel):
    """HTTP-результат сценария UpdateChannel."""

    id: UUID
    revision: int
    verification_job_id: UUID
