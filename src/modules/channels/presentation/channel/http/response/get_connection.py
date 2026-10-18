from uuid import UUID
from pydantic import BaseModel


class GetConnectionResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария get_connection."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    endpoint: str
    locales: tuple[str, ...]
    currency: str | None
    resource_identity: str | None
    verification_status: str
    verification_job_id: UUID | None
    generation: int
    is_paused: bool
    credentials_present: bool
    candidate_present: bool
    reason_code: str | None
    scope_limitations: tuple[str, ...]
