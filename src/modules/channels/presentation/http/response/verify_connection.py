from uuid import UUID

from pydantic import BaseModel


class VerifyConnectionResponse(BaseModel):
    """HTTP-результат сценария VerifyConnection."""

    id: UUID
    revision: int
    verification_job_id: UUID
